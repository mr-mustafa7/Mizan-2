"""Dashboard and summary outputs for Mizan coordinators."""

from __future__ import annotations

from dataclasses import dataclass

from mizan.loader import MizanData
from mizan.matcher import MatchTier, PatientTrialMatch


@dataclass(frozen=True)
class AtRiskTrial:
    trial_id: str
    title: str
    therapeutic_area: str
    phase: str
    sponsor: str
    enrollment_count: int
    target_enrollment: int
    shortfall: int
    fill_pct: float


@dataclass(frozen=True)
class TrialSummary:
    trial_id: str
    trial_title: str
    eligible_count: int
    needs_screening_count: int
    review_count: int
    not_eligible_count: int


@dataclass(frozen=True)
class CoordinatorDashboardRow:
    trial_id: str
    title: str
    phase: str
    sponsor: str
    enrollment_count: int
    target_enrollment: int
    shortfall: int
    eligible_count: int
    needs_screening_count: int
    review_count: int


@dataclass(frozen=True)
class DiagnosisSummaryRow:
    diagnosis: str
    eligible_patient_count: int
    needs_screening_patient_count: int


def at_risk_trials(data: MizanData) -> list[AtRiskTrial]:
    """Recruiting trials filled to less than half their target, sorted by shortfall."""
    rows: list[AtRiskTrial] = []
    for trial in data.trials:
        if trial.status != "recruiting":
            continue
        if trial.target_enrollment <= 0:
            continue
        fill_pct = trial.enrollment_count / trial.target_enrollment
        if fill_pct >= 0.5:
            continue
        rows.append(
            AtRiskTrial(
                trial_id=trial.trial_id,
                title=trial.title,
                therapeutic_area=trial.therapeutic_area,
                phase=trial.phase,
                sponsor=trial.sponsor,
                enrollment_count=trial.enrollment_count,
                target_enrollment=trial.target_enrollment,
                shortfall=trial.target_enrollment - trial.enrollment_count,
                fill_pct=round(fill_pct * 100, 1),
            )
        )
    rows.sort(key=lambda r: (-r.shortfall, r.trial_id))
    return rows


def trial_summaries(matches: list[PatientTrialMatch]) -> list[TrialSummary]:
    """Per-trial counts of patients in each match tier."""
    counts: dict[str, dict[str, int | str]] = {}
    for match in matches:
        bucket = counts.setdefault(
            match.trial_id,
            {
                "trial_id": match.trial_id,
                "trial_title": match.trial_title,
                "eligible_count": 0,
                "needs_screening_count": 0,
                "review_count": 0,
                "not_eligible_count": 0,
            },
        )
        if match.tier == MatchTier.ELIGIBLE:
            bucket["eligible_count"] = int(bucket["eligible_count"]) + 1
        elif match.tier == MatchTier.NEEDS_SCREENING:
            bucket["needs_screening_count"] = int(bucket["needs_screening_count"]) + 1
        elif match.tier == MatchTier.REVIEW:
            bucket["review_count"] = int(bucket["review_count"]) + 1
        else:
            bucket["not_eligible_count"] = int(bucket["not_eligible_count"]) + 1

    return [
        TrialSummary(
            trial_id=str(v["trial_id"]),
            trial_title=str(v["trial_title"]),
            eligible_count=int(v["eligible_count"]),
            needs_screening_count=int(v["needs_screening_count"]),
            review_count=int(v["review_count"]),
            not_eligible_count=int(v["not_eligible_count"]),
        )
        for v in sorted(counts.values(), key=lambda x: str(x["trial_id"]))
    ]


def coordinator_dashboard(
    data: MizanData, matches: list[PatientTrialMatch]
) -> list[CoordinatorDashboardRow]:
    """At-risk trials with eligible / needs-screening / review patient counts."""
    summaries = {s.trial_id: s for s in trial_summaries(matches)}
    rows: list[CoordinatorDashboardRow] = []
    for at_risk in at_risk_trials(data):
        summary = summaries.get(
            at_risk.trial_id,
            TrialSummary(at_risk.trial_id, at_risk.title, 0, 0, 0, 0),
        )
        rows.append(
            CoordinatorDashboardRow(
                trial_id=at_risk.trial_id,
                title=at_risk.title,
                phase=at_risk.phase,
                sponsor=at_risk.sponsor,
                enrollment_count=at_risk.enrollment_count,
                target_enrollment=at_risk.target_enrollment,
                shortfall=at_risk.shortfall,
                eligible_count=summary.eligible_count,
                needs_screening_count=summary.needs_screening_count,
                review_count=summary.review_count,
            )
        )
    return rows


def _patient_diagnosis(data: MizanData, patient_id: str) -> str | None:
    for fact in data.patient_facts:
        if fact.patient_id == patient_id and fact.field_name == "diagnosis" and not fact.negated:
            return fact.str_value
    return None


def diagnosis_summary(data: MizanData, matches: list[PatientTrialMatch]) -> list[DiagnosisSummaryRow]:
    """Distinct ELIGIBLE and NEEDS_SCREENING patients grouped by diagnosis."""
    eligible = {m.patient_id for m in matches if m.tier == MatchTier.ELIGIBLE}
    screening = {m.patient_id for m in matches if m.tier == MatchTier.NEEDS_SCREENING}
    all_patients = eligible | screening

    elig_by_diag: dict[str, set[str]] = {}
    screen_by_diag: dict[str, set[str]] = {}
    for patient_id in all_patients:
        diagnosis = _patient_diagnosis(data, patient_id)
        if not diagnosis:
            continue
        if patient_id in eligible:
            elig_by_diag.setdefault(diagnosis, set()).add(patient_id)
        if patient_id in screening:
            screen_by_diag.setdefault(diagnosis, set()).add(patient_id)

    diagnoses = set(elig_by_diag) | set(screen_by_diag)
    rows = [
        DiagnosisSummaryRow(
            diagnosis=diag,
            eligible_patient_count=len(elig_by_diag.get(diag, set())),
            needs_screening_patient_count=len(screen_by_diag.get(diag, set())),
        )
        for diag in diagnoses
    ]
    rows.sort(key=lambda r: (-r.eligible_patient_count, -r.needs_screening_patient_count, r.diagnosis))
    return rows
