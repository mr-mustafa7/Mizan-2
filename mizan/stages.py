"""Five foundation pipeline stages aligned with Prometheux Vadalog concepts."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from mizan.architecture import DEFAULT_SHORTLIST_SIZE, LAYER_DESCRIPTIONS, Layer
from mizan.dashboards import (
    at_risk_trials,
    coordinator_dashboard,
    diagnosis_summary,
    trial_summaries,
)
from mizan.loader import MizanData, load_mizan_data
from mizan.matcher import (
    AuditRecord,
    PatientTrialMatch,
    build_audit_trail,
    build_criterion_coverage,
    build_rejection_reasons,
    match_all,
)
from mizan.quality import build_patient_data_quality


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
    match_score: float
    soft_rules_met: int
    soft_rules_total: int
    location_bonus: float


def stage_ingest(data_dir: str) -> tuple[MizanData, StageResult]:
    data = load_mizan_data(data_dir)
    quality = build_patient_data_quality(data)
    total = (
        len(data.patients)
        + len(data.patient_facts)
        + len(data.eligibility_criteria)
        + len(data.trials)
        + len(data.sites)
        + len(quality)
    )
    return data, StageResult(
        layer=Layer.INGEST,
        description=LAYER_DESCRIPTIONS[Layer.INGEST],
        row_count=total,
        artifact="data/*.csv + patient_data_quality",
    )


def stage_prefilter(data: MizanData) -> tuple[list[str], StageResult]:
    """Keep recruiting trials with eligibility criteria."""
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
    """Criterion-level evaluation (criterion_evaluation → audit_trail)."""
    records = build_audit_trail(data, trial_ids)
    return records, StageResult(
        layer=Layer.ELIGIBILITY,
        description="One audit row per patient × trial × supported criterion",
        row_count=len(records),
        artifact="audit_trail.csv",
    )


def stage_ranking(
    data: MizanData,
    trial_ids: list[str],
    audit: list[AuditRecord],
) -> tuple[list[PatientTrialMatch], StageResult]:
    """Pair assessment: tier + match score per patient-trial pair."""
    _, matches = match_all(data, trial_ids)
    return matches, StageResult(
        layer=Layer.RANKING,
        description="pair_assessment tiers and match scores",
        row_count=len(matches),
        artifact="pair_assessment.csv",
    )


def patient_shortlists(
    matches: list[PatientTrialMatch],
    top_k: int = DEFAULT_SHORTLIST_SIZE,
) -> list[PatientShortlistRow]:
    """Top-K trials per patient by match score."""
    rows: list[PatientShortlistRow] = []
    patient_ids = sorted({m.patient_id for m in matches})
    for patient_id in patient_ids:
        patient_matches = [m for m in matches if m.patient_id == patient_id]
        patient_matches.sort(key=lambda m: (-m.score, m.trial_id))
        for rank, match in enumerate(patient_matches[:top_k], start=1):
            rows.append(
                PatientShortlistRow(
                    patient_id=match.patient_id,
                    rank=rank,
                    trial_id=match.trial_id,
                    trial_title=match.trial_title,
                    tier=match.tier.value,
                    match_score=match.score,
                    soft_rules_met=match.soft_rules_met,
                    soft_rules_total=match.soft_rules_total,
                    location_bonus=match.location_bonus,
                )
            )
    return rows


def stage_decision_support(
    data: MizanData,
    matches: list[PatientTrialMatch],
    audit: list[AuditRecord],
    shortlists: list[PatientShortlistRow],
) -> tuple[dict, StageResult]:
    """Coordinator-facing outputs."""
    quality = build_patient_data_quality(data)
    rejections = build_rejection_reasons(matches, audit)
    active_trials = sorted({m.trial_id for m in matches})
    coverage = build_criterion_coverage(data, active_trials)
    payload = {
        "patient_data_quality": [asdict(r) for r in quality],
        "at_risk_trials": [asdict(r) for r in at_risk_trials(data)],
        "coordinator_dashboard": [asdict(r) for r in coordinator_dashboard(data, matches)],
        "trial_summary": [asdict(r) for r in trial_summaries(matches)],
        "diagnosis_summary": [asdict(r) for r in diagnosis_summary(data, matches)],
        "rejection_reason": [asdict(r) for r in rejections],
        "criterion_coverage": [asdict(r) for r in coverage],
        "patient_shortlists": [asdict(r) for r in shortlists],
        "tier_counts": _tier_counts(matches),
    }
    total_rows = sum(
        len(payload[k])
        for k in (
            "patient_data_quality",
            "at_risk_trials",
            "coordinator_dashboard",
            "trial_summary",
            "diagnosis_summary",
            "rejection_reason",
            "criterion_coverage",
            "patient_shortlists",
        )
    )
    return payload, StageResult(
        layer=Layer.DECISION_SUPPORT,
        description="At-risk trials, coordinator dashboard, rejection reasons",
        row_count=total_rows,
        artifact="coordinator_dashboard.csv + patient_shortlists.csv",
    )


def _tier_counts(matches: list[PatientTrialMatch]) -> dict[str, int]:
    from mizan.matcher import MatchTier

    counts = {tier.value: 0 for tier in MatchTier}
    for match in matches:
        counts[match.tier.value] += 1
    return counts
