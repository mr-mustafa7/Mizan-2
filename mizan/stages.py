"""Five foundation pipeline stages for demo and production extension."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from mizan.architecture import DEFAULT_SHORTLIST_SIZE, LAYER_DESCRIPTIONS, Layer
from mizan.dashboards import (
    at_risk_trials,
    coordinator_dashboard,
    diagnosis_summary,
    trial_summaries,
)
from mizan.evaluator import CriterionResult, EvaluationOutcome, evaluate_criterion
from mizan.loader import MizanData, load_mizan_data
from mizan.matcher import (
    AuditRecord,
    MatchTier,
    PatientTrialMatch,
    _classify_tier,
    _criteria_for_trial,
    _location_bonus,
    _trial_lookup,
    build_audit_trail,
)
from mizan.scoring import composite_score


@dataclass
class StageResult:
    layer: Layer
    description: str
    row_count: int
    artifact: str


@dataclass(frozen=True)
class PatientShortlistRow:
    patient_id: str
    rank: int
    trial_id: str
    trial_title: str
    tier: str
    composite_score: float
    final_score: float
    inclusion_score: float
    exclusion_score: float


def stage_ingest(data_dir: str) -> tuple[MizanData, StageResult]:
    data = load_mizan_data(data_dir)
    total = (
        len(data.patients)
        + len(data.patient_facts)
        + len(data.eligibility_criteria)
        + len(data.trials)
        + len(data.sites)
    )
    return data, StageResult(
        layer=Layer.INGEST,
        description=LAYER_DESCRIPTIONS[Layer.INGEST],
        row_count=total,
        artifact="data/*.csv",
    )


def stage_prefilter(data: MizanData) -> tuple[list[str], StageResult]:
    """Keep recruiting trials with eligibility criteria (fast deterministic gate)."""
    trial_ids_with_rules = {c.trial_id for c in data.eligibility_criteria}
    active = [
        t.trial_id
        for t in data.trials
        if t.status == "recruiting" and t.trial_id in trial_ids_with_rules
    ]
    return active, StageResult(
        layer=Layer.PREFILTER,
        description=f"{len(active)} recruiting trials passed prefilter",
        row_count=len(active),
        artifact="prefilter/recruiting_trials",
    )


def stage_eligibility(data: MizanData, trial_ids: list[str]) -> tuple[list[AuditRecord], StageResult]:
    """Criterion-level evaluation with audit trail."""
    records: list[AuditRecord] = []
    for patient in data.patients:
        for trial_id in trial_ids:
            for criterion in _criteria_for_trial(data, trial_id):
                outcome = evaluate_criterion(data, patient.patient_id, criterion)
                records.append(
                    AuditRecord(
                        patient_id=patient.patient_id,
                        trial_id=trial_id,
                        criterion_id=criterion.criterion_id,
                        field_checked=criterion.field_checked,
                        rule_type=criterion.rule_type,
                        hard_gate=criterion.hard_gate,
                        result=outcome.result.value,
                        reason=outcome.reason,
                        patient_info=outcome.patient_info,
                        criterion_text=criterion.criterion_text
                        or f"{criterion.rule_type} {criterion.field_checked} {criterion.operator} {criterion.value}",
                    )
                )
    return records, StageResult(
        layer=Layer.ELIGIBILITY,
        description="One audit row per patient × trial × criterion",
        row_count=len(records),
        artifact="audit_trail.csv",
    )


def stage_ranking(
    data: MizanData,
    trial_ids: list[str],
    audit: list[AuditRecord],
) -> tuple[list[PatientTrialMatch], StageResult]:
    """Score and classify every patient–trial pair."""
    audit_index = {(r.patient_id, r.trial_id, r.criterion_id): r for r in audit}
    matches: list[PatientTrialMatch] = []

    for patient in data.patients:
        for trial_id in trial_ids:
            trial = _trial_lookup(data, trial_id)
            if trial is None:
                continue

            criteria = _criteria_for_trial(data, trial_id)
            outcomes: list[tuple] = []
            for criterion in criteria:
                record = audit_index[(patient.patient_id, trial_id, criterion.criterion_id)]
                outcomes.append(
                    (
                        criterion,
                        EvaluationOutcome(
                            CriterionResult(record.result),
                            record.reason,
                            record.patient_info,
                        ),
                    )
                )

            hard = [
                (c, o)
                for c, o in outcomes
                if c.hard_gate and o.result != CriterionResult.NOT_APPLICABLE
            ]
            hard_failures = sum(1 for _, o in hard if o.result == CriterionResult.NOT_MET)
            hard_unknowns = sum(1 for _, o in hard if o.result == CriterionResult.UNKNOWN)

            soft = [
                (c, o)
                for c, o in outcomes
                if not c.hard_gate and o.result != CriterionResult.NOT_APPLICABLE
            ]
            soft_met = sum(1 for _, o in soft if o.result == CriterionResult.MET)
            soft_total = len(soft)
            soft_unknown = sum(1 for _, o in soft if o.result == CriterionResult.UNKNOWN)
            soft_failed = sum(1 for _, o in soft if o.result == CriterionResult.NOT_MET)

            loc_bonus = 0.0 if hard_failures else _location_bonus(data, patient, trial_id)
            scores = composite_score(outcomes, location_bonus=loc_bonus)

            tier = _classify_tier(
                hard_failures=hard_failures,
                hard_unknowns=hard_unknowns,
                soft_failures=soft_failed,
                soft_unknowns=soft_unknown,
                soft_total=soft_total,
                soft_met=soft_met,
                score=scores.final_score,
            )

            matches.append(
                PatientTrialMatch(
                    patient_id=patient.patient_id,
                    trial_id=trial_id,
                    trial_title=trial.title,
                    tier=tier,
                    score=scores.final_score,
                    soft_rules_met=soft_met,
                    soft_rules_total=soft_total,
                    soft_rules_unknown=soft_unknown,
                    location_bonus=loc_bonus,
                    hard_failures=hard_failures,
                    hard_unknowns=hard_unknowns,
                    soft_failures=soft_failed,
                )
            )

    matches.sort(key=lambda m: (m.trial_id, -m.score, m.patient_id))
    return matches, StageResult(
        layer=Layer.RANKING,
        description="Composite score + tier classification",
        row_count=len(matches),
        artifact="patient_trial_matches.csv",
    )


def patient_shortlists(
    matches: list[PatientTrialMatch],
    audit: list[AuditRecord],
    data: MizanData,
    top_k: int = DEFAULT_SHORTLIST_SIZE,
) -> list[PatientShortlistRow]:
    """Top-K trials per patient (TrialMatchAI WIDE study used top-20)."""
    audit_by_pair: dict[tuple[str, str], list[AuditRecord]] = {}
    for row in audit:
        audit_by_pair.setdefault((row.patient_id, row.trial_id), []).append(row)

    rows: list[PatientShortlistRow] = []
    for patient in data.patients:
        patient_matches = [m for m in matches if m.patient_id == patient.patient_id]
        patient_matches.sort(key=lambda m: (-m.score, m.trial_id))
        for rank, match in enumerate(patient_matches[:top_k], start=1):
            pair_audit = audit_by_pair.get((match.patient_id, match.trial_id), [])
            outcomes = []
            for record in pair_audit:
                criterion = next(
                    c
                    for c in _criteria_for_trial(data, match.trial_id)
                    if c.criterion_id == record.criterion_id
                )
                outcomes.append(
                    (
                        criterion,
                        EvaluationOutcome(
                            CriterionResult(record.result),
                            record.reason,
                            record.patient_info,
                        ),
                    )
                )
            scores = composite_score(outcomes, location_bonus=match.location_bonus)
            rows.append(
                PatientShortlistRow(
                    patient_id=match.patient_id,
                    rank=rank,
                    trial_id=match.trial_id,
                    trial_title=match.trial_title,
                    tier=match.tier.value,
                    composite_score=scores.composite_score,
                    final_score=match.score,
                    inclusion_score=scores.inclusion_score,
                    exclusion_score=scores.exclusion_score,
                )
            )
    return rows


def stage_decision_support(
    data: MizanData,
    matches: list[PatientTrialMatch],
    shortlists: list[PatientShortlistRow],
) -> tuple[dict, StageResult]:
    """Coordinator-facing outputs."""
    payload = {
        "at_risk_trials": [asdict(r) for r in at_risk_trials(data)],
        "coordinator_dashboard": [asdict(r) for r in coordinator_dashboard(data, matches)],
        "trial_summary": [asdict(r) for r in trial_summaries(matches)],
        "diagnosis_summary": [asdict(r) for r in diagnosis_summary(data, matches)],
        "patient_shortlists": [asdict(r) for r in shortlists],
        "tier_counts": _tier_counts(matches),
    }
    total_rows = (
        len(payload["at_risk_trials"])
        + len(payload["coordinator_dashboard"])
        + len(payload["trial_summary"])
        + len(payload["diagnosis_summary"])
        + len(payload["patient_shortlists"])
    )
    return payload, StageResult(
        layer=Layer.DECISION_SUPPORT,
        description="At-risk trials, coordinator dashboard, shortlists",
        row_count=total_rows,
        artifact="coordinator_dashboard.csv + patient_shortlists.csv",
    )


def _tier_counts(matches: list[PatientTrialMatch]) -> dict[str, int]:
    counts = {tier.value: 0 for tier in MatchTier}
    for match in matches:
        counts[match.tier.value] += 1
    return counts

