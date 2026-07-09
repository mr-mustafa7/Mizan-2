"""Orchestrate the full Mizan matching pipeline."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mizan.dashboards import (
    at_risk_trials,
    coordinator_dashboard,
    diagnosis_summary,
    trial_summaries,
)
from mizan.loader import load_mizan_data, summarize_inputs
from mizan.matcher import match_all


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
    """Load data, run matching, write outputs, return row counts."""
    data = load_mizan_data(data_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    audit, matches = match_all(data)

    audit_rows = [asdict(r) for r in audit]
    match_rows = [asdict(m) for m in matches]
    for row in match_rows:
        row["tier"] = row["tier"].value if hasattr(row["tier"], "value") else row["tier"]

    at_risk_rows = [asdict(r) for r in at_risk_trials(data)]
    trial_summary_rows = [asdict(r) for r in trial_summaries(matches)]
    coordinator_rows = [asdict(r) for r in coordinator_dashboard(data, matches)]
    diagnosis_rows = [asdict(r) for r in diagnosis_summary(data, matches)]

    counts = {
        "audit_trail": _write_csv(out / "audit_trail.csv", audit_rows),
        "patient_trial_matches": _write_csv(out / "patient_trial_matches.csv", match_rows),
        "at_risk_trials": _write_csv(out / "at_risk_trials.csv", at_risk_rows),
        "trial_summary": _write_csv(out / "trial_summary.csv", trial_summary_rows),
        "coordinator_dashboard": _write_csv(out / "coordinator_dashboard.csv", coordinator_rows),
        "diagnosis_summary": _write_csv(out / "diagnosis_summary.csv", diagnosis_rows),
    }

    report = {
        "inputs": summarize_inputs(data),
        "output_row_counts": counts,
        "logic_checks": _logic_checks(data, audit_rows, match_rows),
    }
    (out / "pipeline_report.json").write_text(json.dumps(report, indent=2))
    return report


def _logic_checks(data, audit_rows: list[dict], match_rows: list[dict]) -> dict[str, Any]:
    """Sanity checks that scores align with audit results."""
    issues: list[str] = []

    expected_audit = len(data.patients) * len(data.trials) * len(data.eligibility_criteria)
    # Criteria are per-trial, not global.
    criteria_by_trial = {}
    for c in data.eligibility_criteria:
        criteria_by_trial.setdefault(c.trial_id, 0)
        criteria_by_trial[c.trial_id] += 1
    expected_audit = sum(
        len(data.patients) * criteria_by_trial.get(t.trial_id, 0) for t in data.trials
    )
    if len(audit_rows) != expected_audit:
        issues.append(
            f"Audit row count {len(audit_rows)} != expected {expected_audit} "
            "(patients x trial-specific criteria)"
        )

    expected_matches = len(data.patients) * len(data.trials)
    if len(match_rows) != expected_matches:
        issues.append(
            f"Match row count {len(match_rows)} != expected {expected_matches} (patients x trials)"
        )

    # NOT_ELIGIBLE must have at least one hard NOT_MET in audit for that pair.
    audit_by_pair: dict[tuple[str, str], list[dict]] = {}
    for row in audit_rows:
        key = (row["patient_id"], row["trial_id"])
        audit_by_pair.setdefault(key, []).append(row)

    for match in match_rows:
        if match["tier"] != "NOT_ELIGIBLE":
            continue
        pair_audit = audit_by_pair.get((match["patient_id"], match["trial_id"]), [])
        hard_not_met = [
            r
            for r in pair_audit
            if r["hard_gate"] and r["result"] == "NOT_MET"
        ]
        if not hard_not_met:
            issues.append(
                f"NOT_ELIGIBLE pair {match['patient_id']}/{match['trial_id']} has no hard NOT_MET audit row"
            )

    # NEEDS_SCREENING should not have hard NOT_MET.
    for match in match_rows:
        if match["tier"] != "NEEDS_SCREENING":
            continue
        pair_audit = audit_by_pair.get((match["patient_id"], match["trial_id"]), [])
        if any(r["hard_gate"] and r["result"] == "NOT_MET" for r in pair_audit):
            issues.append(
                f"NEEDS_SCREENING pair {match['patient_id']}/{match['trial_id']} has hard NOT_MET"
            )

    return {"passed": len(issues) == 0, "issues": issues}
