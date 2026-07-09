"""Run the five-layer Mizan foundation pipeline."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mizan.architecture import FOUNDATION_REFERENCES, Layer
from mizan.loader import summarize_inputs
from mizan.stages import (
    patient_shortlists,
    stage_decision_support,
    stage_eligibility,
    stage_ingest,
    stage_prefilter,
    stage_ranking,
)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return 0
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def run_pipeline(data_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Execute all five foundation layers and write demo artifacts."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    data, ingest = stage_ingest(str(data_dir))
    trial_ids, prefilter = stage_prefilter(data)
    audit, eligibility = stage_eligibility(data, trial_ids)
    matches, ranking = stage_ranking(data, trial_ids, audit)
    shortlists = patient_shortlists(matches)
    decision, decision_stage = stage_decision_support(data, matches, audit, shortlists)

    from mizan.explanation import build_all_explanations

    explanations = build_all_explanations(data, trial_ids)

    audit_rows = [asdict(r) for r in audit]
    match_rows = [asdict(m) for m in matches]
    for row in match_rows:
        row["tier"] = row["tier"].value if hasattr(row["tier"], "value") else row["tier"]

    counts = {
        "patient_data_quality": _write_csv(out / "patient_data_quality.csv", decision["patient_data_quality"]),
        "audit_trail": _write_csv(out / "audit_trail.csv", audit_rows),
        "pair_assessment": _write_csv(out / "pair_assessment.csv", match_rows),
        "rejection_reason": _write_csv(out / "rejection_reason.csv", decision["rejection_reason"]),
        "criterion_coverage": _write_csv(out / "criterion_coverage.csv", decision["criterion_coverage"]),
        "patient_shortlists": _write_csv(out / "patient_shortlists.csv", decision["patient_shortlists"]),
        "at_risk_trials": _write_csv(out / "at_risk_trials.csv", decision["at_risk_trials"]),
        "coordinator_dashboard": _write_csv(out / "coordinator_dashboard.csv", decision["coordinator_dashboard"]),
        "trial_summary": _write_csv(out / "trial_summary.csv", decision["trial_summary"]),
        "diagnosis_summary": _write_csv(out / "diagnosis_summary.csv", decision["diagnosis_summary"]),
        "match_explanations": len(explanations),
    }

    explanation_payload = [e.to_dict() for e in explanations]
    (out / "match_explanations.json").write_text(json.dumps(explanation_payload, indent=2))

    stages = [ingest, prefilter, eligibility, ranking, decision_stage]
    report = {
        "architecture": "mizan_prometheux_vadalog",
        "layers": [
            {
                "id": s.layer.value,
                "name": s.layer.name,
                "description": s.description,
                "row_count": s.row_count,
                "artifact": s.artifact,
            }
            for s in stages
        ],
        "research_basis": [asdict(r) for r in FOUNDATION_REFERENCES],
        "inputs": summarize_inputs(data),
        "output_row_counts": counts,
        "tier_counts": decision["tier_counts"],
        "criterion_coverage": _coverage_summary(decision["criterion_coverage"]),
        "prefiltered_trials": trial_ids,
        "logic_checks": _logic_checks(data, trial_ids, audit_rows, match_rows),
    }
    (out / "pipeline_report.json").write_text(json.dumps(report, indent=2))
    (out / "demo_summary.json").write_text(json.dumps(_demo_summary(report, decision), indent=2))
    return report


def _coverage_summary(coverage_rows: list[dict]) -> dict[str, Any]:
    dropped = [r for r in coverage_rows if r["evaluated"] == "NO"]
    return {
        "total_criteria": len(coverage_rows),
        "evaluated": len(coverage_rows) - len(dropped),
        "dropped": len(dropped),
        "dropped_criteria": [
            {
                "criterion_id": r["criterion_id"],
                "trial_id": r["trial_id"],
                "field_checked": r["field_checked"],
                "note": r["note"],
            }
            for r in dropped
        ],
    }


def _demo_summary(report: dict, decision: dict) -> dict:
    at_risk = decision["at_risk_trials"]
    top_shortfall = at_risk[0] if at_risk else None
    quality = decision["patient_data_quality"]
    excluded = [q for q in quality if q["scoreable"] != "YES"]
    return {
        "headline": "Mizan coordinator decision-support demo (Prometheux Vadalog)",
        "patients": report["inputs"]["row_counts"]["patients"],
        "scoreable_patients": len(quality) - len(excluded),
        "excluded_patients": len(excluded),
        "recruiting_trials_evaluated": len(report["prefiltered_trials"]),
        "at_risk_trials": len(at_risk),
        "top_shortfall_trial": top_shortfall,
        "tier_counts": report["tier_counts"],
        "needs_screening_highlight": report["tier_counts"].get("NEEDS_SCREENING", 0),
        "criterion_coverage": report["criterion_coverage"],
        "layers_completed": len(report["layers"]),
    }


def _logic_checks(data, trial_ids, audit_rows, match_rows) -> dict[str, Any]:
    from mizan.evaluator import is_supported_criterion

    issues: list[str] = []
    supported_per_trial: dict[str, int] = {}
    for c in data.eligibility_criteria:
        if c.trial_id in trial_ids and is_supported_criterion(c):
            supported_per_trial[c.trial_id] = supported_per_trial.get(c.trial_id, 0) + 1

    expected_audit = sum(len(data.patients) * supported_per_trial.get(tid, 0) for tid in trial_ids)
    if len(audit_rows) != expected_audit:
        issues.append(f"Audit rows {len(audit_rows)} != expected {expected_audit}")

    expected_matches = len(match_rows)
    pairs_with_rules = sum(1 for tid in trial_ids if supported_per_trial.get(tid, 0) > 0)
    expected_pairs = len(data.patients) * pairs_with_rules
    if expected_matches != expected_pairs:
        issues.append(f"Match rows {expected_matches} != expected {expected_pairs}")

    audit_by_pair: dict[tuple[str, str], list[dict]] = {}
    for row in audit_rows:
        audit_by_pair.setdefault((row["patient_id"], row["trial_id"]), []).append(row)

    for match in match_rows:
        if match["tier"] == "NOT_ELIGIBLE":
            pair = audit_by_pair.get((match["patient_id"], match["trial_id"]), [])
            if not any(r["hard_gate"] and r["result"] == "NOT_MET" for r in pair):
                issues.append(f"NOT_ELIGIBLE without hard NOT_MET: {match['patient_id']}/{match['trial_id']}")

    return {"passed": len(issues) == 0, "issues": issues}
