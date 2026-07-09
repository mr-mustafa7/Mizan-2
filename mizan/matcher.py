"""Patient-trial pair assessment (Prometheux pair_assessment concept)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mizan.evaluator import CriterionResult, EvaluationOutcome, build_criterion_evaluation, evaluate_criterion
from mizan.loader import EligibilityCriterion, MizanData, Patient


class MatchTier(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NEEDS_SCREENING = "NEEDS_SCREENING"
    REVIEW = "REVIEW"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


CITY_BONUS = 25
COUNTRY_BONUS = 15


@dataclass(frozen=True)
class CriterionEvaluationRow:
    criterion_id: str
    patient_id: str
    trial_id: str
    field_checked: str
    comparator: str
    polarity: str
    hard_gate: bool
    result: str
    reason: str
    source_text: str


@dataclass(frozen=True)
class AuditRecord:
    patient_id: str
    age: int
    sex: str
    city: str
    trial_id: str
    criterion_id: str
    field_checked: str
    hard_gate: bool
    result: str
    reason: str
    rule_text: str


@dataclass(frozen=True)
class PatientTrialMatch:
    patient_id: str
    trial_id: str
    trial_title: str
    tier: MatchTier
    score: float
    soft_rules_met: int
    soft_rules_total: int
    location_bonus: float


@dataclass(frozen=True)
class RejectionReason:
    patient_id: str
    trial_id: str
    criterion_id: str
    field_checked: str
    hard_gate: bool
    reason: str


def _criteria_for_trial(data: MizanData, trial_id: str) -> list[EligibilityCriterion]:
    return [c for c in data.eligibility_criteria if c.trial_id == trial_id]


def _trial_lookup(data: MizanData, trial_id: str):
    for trial in data.trials:
        if trial.trial_id == trial_id:
            return trial
    return None


def _patient_lookup(data: MizanData, patient_id: str) -> Patient | None:
    for patient in data.patients:
        if patient.patient_id == patient_id:
            return patient
    return None


def _city_match(data: MizanData, patient: Patient, trial_id: str) -> bool:
    for site in data.sites:
        if site.trial_id == trial_id and site.city.strip().lower() == patient.city.strip().lower():
            if patient.city.strip():
                return True
    return False


def _country_match(data: MizanData, patient: Patient, trial_id: str) -> bool:
    if _city_match(data, patient, trial_id):
        return False
    for site in data.sites:
        if site.trial_id == trial_id and site.country.strip().lower() == patient.country.strip().lower():
            if patient.country.strip():
                return True
    return False


def _location_bonus(data: MizanData, patient: Patient, trial_id: str) -> int:
    if _city_match(data, patient, trial_id):
        return CITY_BONUS
    if _country_match(data, patient, trial_id):
        return COUNTRY_BONUS
    return 0


def _soft_pct(soft_met: int, soft_total: int) -> int:
    if soft_total == 0:
        return 100
    return (100 * soft_met) // soft_total


def _classify_pair(
    hard_fail: bool,
    hard_unknown: bool,
    soft_met: int,
    soft_total: int,
) -> MatchTier:
    if hard_fail:
        return MatchTier.NOT_ELIGIBLE
    if hard_unknown:
        return MatchTier.NEEDS_SCREENING
    if 2 * soft_met >= soft_total:
        return MatchTier.ELIGIBLE
    return MatchTier.REVIEW


def _pair_outcomes(
    data: MizanData, patient_id: str, trial_id: str
) -> list[tuple[EligibilityCriterion, EvaluationOutcome]]:
    outcomes: list[tuple[EligibilityCriterion, EvaluationOutcome]] = []
    for criterion in _criteria_for_trial(data, trial_id):
        outcome = evaluate_criterion(data, patient_id, criterion)
        if outcome is not None:
            outcomes.append((criterion, outcome))
    return outcomes


def build_criterion_evaluation_rows(
    data: MizanData, trial_ids: list[str] | None = None
) -> list[CriterionEvaluationRow]:
    rows: list[CriterionEvaluationRow] = []
    for criterion, patient_id, outcome in build_criterion_evaluation(data, trial_ids):
        rows.append(
            CriterionEvaluationRow(
                criterion_id=criterion.criterion_id,
                patient_id=patient_id,
                trial_id=criterion.trial_id,
                field_checked=criterion.field_checked,
                comparator=criterion.operator,
                polarity=criterion.rule_type,
                hard_gate=criterion.hard_gate,
                result=outcome.result.value,
                reason=outcome.reason,
                source_text=outcome.source_text,
            )
        )
    return rows


def build_audit_trail(data: MizanData, trial_ids: list[str] | None = None) -> list[AuditRecord]:
    """GCP audit trail derived from criterion_evaluation."""
    records: list[AuditRecord] = []
    for row in build_criterion_evaluation_rows(data, trial_ids):
        patient = _patient_lookup(data, row.patient_id)
        if patient is None:
            continue
        records.append(
            AuditRecord(
                patient_id=row.patient_id,
                age=patient.age,
                sex=patient.sex,
                city=patient.city,
                trial_id=row.trial_id,
                criterion_id=row.criterion_id,
                field_checked=row.field_checked,
                hard_gate=row.hard_gate,
                result=row.result,
                reason=row.reason,
                rule_text=row.source_text,
            )
        )
    return records


def match_patient_trial(data: MizanData, patient_id: str, trial_id: str) -> PatientTrialMatch | None:
    """Score and classify one patient-trial pair (pair_assessment)."""
    trial = _trial_lookup(data, trial_id)
    patient = _patient_lookup(data, patient_id)
    if trial is None or patient is None:
        return None

    outcomes = _pair_outcomes(data, patient_id, trial_id)
    if not outcomes:
        return None

    hard = [(c, o) for c, o in outcomes if c.hard_gate]
    hard_fail = any(o.result == CriterionResult.NOT_MET for _, o in hard)
    hard_unknown = any(o.result == CriterionResult.UNKNOWN for _, o in hard)

    soft = [(c, o) for c, o in outcomes if not c.hard_gate]
    soft_met = sum(1 for _, o in soft if o.result == CriterionResult.MET)
    soft_total = len(soft)

    tier = _classify_pair(hard_fail, hard_unknown, soft_met, soft_total)
    loc_bonus = 0 if hard_fail else _location_bonus(data, patient, trial_id)
    pct = _soft_pct(soft_met, soft_total)
    score = 0.0 if hard_fail else float(pct + loc_bonus)

    return PatientTrialMatch(
        patient_id=patient_id,
        trial_id=trial_id,
        trial_title=trial.title,
        tier=tier,
        score=score,
        soft_rules_met=soft_met,
        soft_rules_total=soft_total,
        location_bonus=float(loc_bonus),
    )


def match_all(
    data: MizanData, trial_ids: list[str] | None = None
) -> tuple[list[AuditRecord], list[PatientTrialMatch]]:
    """Full patient × trial matching for active trials."""
    active = trial_ids or [t.trial_id for t in data.trials if t.status == "recruiting"]
    audit = build_audit_trail(data, active)
    matches: list[PatientTrialMatch] = []
    for patient in data.patients:
        for trial_id in active:
            match = match_patient_trial(data, patient.patient_id, trial_id)
            if match is not None:
                matches.append(match)
    matches.sort(key=lambda m: (m.trial_id, -m.score, m.patient_id))
    return audit, matches


def build_rejection_reasons(matches: list[PatientTrialMatch], audit: list[AuditRecord]) -> list[RejectionReason]:
    """Hard-gate failures for NOT_ELIGIBLE pairs."""
    ineligible = {(m.patient_id, m.trial_id) for m in matches if m.tier == MatchTier.NOT_ELIGIBLE}
    reasons: list[RejectionReason] = []
    for record in audit:
        if (record.patient_id, record.trial_id) not in ineligible:
            continue
        if record.hard_gate and record.result == "NOT_MET":
            reasons.append(
                RejectionReason(
                    patient_id=record.patient_id,
                    trial_id=record.trial_id,
                    criterion_id=record.criterion_id,
                    field_checked=record.field_checked,
                    hard_gate=record.hard_gate,
                    reason=record.reason,
                )
            )
    return reasons
