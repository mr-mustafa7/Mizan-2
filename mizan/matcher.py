"""Patient-trial matching, scoring, classification, and audit trail."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mizan.evaluator import CriterionResult, EvaluationOutcome, evaluate_criterion
from mizan.loader import EligibilityCriterion, MizanData, Patient, Trial


class MatchTier(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NEEDS_SCREENING = "NEEDS_SCREENING"
    REVIEW = "REVIEW"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


CITY_BONUS = 25.0
COUNTRY_BONUS = 15.0


@dataclass(frozen=True)
class AuditRecord:
    patient_id: str
    trial_id: str
    criterion_id: str
    field_checked: str
    rule_type: str
    hard_gate: bool
    result: str
    reason: str
    patient_info: str
    criterion_text: str


@dataclass(frozen=True)
class PatientTrialMatch:
    patient_id: str
    trial_id: str
    trial_title: str
    tier: MatchTier
    score: float
    soft_rules_met: int
    soft_rules_total: int
    soft_rules_unknown: int
    location_bonus: float
    hard_failures: int
    hard_unknowns: int
    soft_failures: int


def _criteria_for_trial(data: MizanData, trial_id: str) -> list[EligibilityCriterion]:
    return [c for c in data.eligibility_criteria if c.trial_id == trial_id]


def _trial_lookup(data: MizanData, trial_id: str) -> Trial | None:
    for trial in data.trials:
        if trial.trial_id == trial_id:
            return trial
    return None


def _patient_lookup(data: MizanData, patient_id: str) -> Patient | None:
    for patient in data.patients:
        if patient.patient_id == patient_id:
            return patient
    return None


def _location_bonus(data: MizanData, patient: Patient, trial_id: str) -> float:
    trial_sites = [s for s in data.sites if s.trial_id == trial_id]
    if not trial_sites:
        return 0.0

    patient_city = patient.city.strip().lower()
    patient_country = patient.country.strip().lower()

    for site in trial_sites:
        if site.city.strip().lower() == patient_city and patient_city:
            return CITY_BONUS
    for site in trial_sites:
        if site.country.strip().lower() == patient_country and patient_country:
            return COUNTRY_BONUS
    return 0.0


def _classify_tier(
    hard_failures: int,
    hard_unknowns: int,
    soft_failures: int,
    soft_unknowns: int,
    soft_total: int,
    soft_met: int,
    score: float,
) -> MatchTier:
    if hard_failures > 0:
        return MatchTier.NOT_ELIGIBLE

    if hard_unknowns > 0 or soft_unknowns > 0:
        return MatchTier.NEEDS_SCREENING

    if soft_failures > 0:
        return MatchTier.REVIEW

    if soft_total == 0:
        return MatchTier.ELIGIBLE

    # Strong fit: all soft rules met (or only N/A) and high composite score.
    if soft_met == soft_total and score >= 70:
        return MatchTier.ELIGIBLE

    if score >= 50:
        return MatchTier.REVIEW

    return MatchTier.REVIEW


def build_audit_trail(data: MizanData) -> list[AuditRecord]:
    """One row per patient x trial x criterion."""
    records: list[AuditRecord] = []
    for patient in data.patients:
        for trial in data.trials:
            for criterion in _criteria_for_trial(data, trial.trial_id):
                outcome = evaluate_criterion(data, patient.patient_id, criterion)
                records.append(
                    AuditRecord(
                        patient_id=patient.patient_id,
                        trial_id=trial.trial_id,
                        criterion_id=criterion.criterion_id,
                        field_checked=criterion.field_checked,
                        rule_type=criterion.rule_type,
                        hard_gate=criterion.hard_gate,
                        result=outcome.result.value,
                        reason=outcome.reason,
                        patient_info=outcome.patient_info,
                        criterion_text=criterion.criterion_text or (
                            f"{criterion.rule_type} {criterion.field_checked} "
                            f"{criterion.operator} {criterion.value}"
                        ),
                    )
                )
    return records


def _score_soft_rules(outcomes: list[tuple[EligibilityCriterion, EvaluationOutcome]]) -> tuple[float, int, int, int, int]:
    soft = [(c, o) for c, o in outcomes if not c.hard_gate and o.result != CriterionResult.NOT_APPLICABLE]
    if not soft:
        return 100.0, 0, 0, 0, 0

    total = len(soft)
    met = sum(1 for _, o in soft if o.result == CriterionResult.MET)
    unknown = sum(1 for _, o in soft if o.result == CriterionResult.UNKNOWN)
    failed = sum(1 for _, o in soft if o.result == CriterionResult.NOT_MET)
    ratio = met / total
    return ratio * 100.0, met, total, unknown, failed


def match_patient_trial(
    data: MizanData, patient_id: str, trial_id: str, audit_index: dict[tuple[str, str, str], AuditRecord] | None = None
) -> PatientTrialMatch:
    """Score and classify a single patient-trial pair using the same logic as the audit trail."""
    trial = _trial_lookup(data, trial_id)
    patient = _patient_lookup(data, patient_id)
    if trial is None or patient is None:
        raise ValueError(f"Unknown patient {patient_id} or trial {trial_id}")

    criteria = _criteria_for_trial(data, trial_id)
    outcomes: list[tuple[EligibilityCriterion, EvaluationOutcome]] = []
    for criterion in criteria:
        if audit_index and (patient_id, trial_id, criterion.criterion_id) in audit_index:
            record = audit_index[(patient_id, trial_id, criterion.criterion_id)]
            outcome = EvaluationOutcome(
                CriterionResult(record.result),
                record.reason,
                record.patient_info,
            )
        else:
            outcome = evaluate_criterion(data, patient_id, criterion)
        outcomes.append((criterion, outcome))

    hard = [
        (c, o)
        for c, o in outcomes
        if c.hard_gate and o.result != CriterionResult.NOT_APPLICABLE
    ]
    hard_failures = sum(1 for _, o in hard if o.result == CriterionResult.NOT_MET)
    hard_unknowns = sum(1 for _, o in hard if o.result == CriterionResult.UNKNOWN)

    soft_score, soft_met, soft_total, soft_unknown, soft_failed = _score_soft_rules(outcomes)
    location_bonus = 0.0 if hard_failures > 0 else _location_bonus(data, patient, trial_id)
    final_score = soft_score + location_bonus if hard_failures == 0 else 0.0

    tier = _classify_tier(
        hard_failures=hard_failures,
        hard_unknowns=hard_unknowns,
        soft_failures=soft_failed,
        soft_unknowns=soft_unknown,
        soft_total=soft_total,
        soft_met=soft_met,
        score=final_score,
    )

    return PatientTrialMatch(
        patient_id=patient_id,
        trial_id=trial_id,
        trial_title=trial.title,
        tier=tier,
        score=round(final_score, 2),
        soft_rules_met=soft_met,
        soft_rules_total=soft_total,
        soft_rules_unknown=soft_unknown,
        location_bonus=location_bonus,
        hard_failures=hard_failures,
        hard_unknowns=hard_unknowns,
        soft_failures=soft_failed,
    )


def match_all(data: MizanData) -> tuple[list[AuditRecord], list[PatientTrialMatch]]:
    """Run full patient x trial matching. Audit trail and scores share one evaluation pass."""
    audit = build_audit_trail(data)
    audit_index = {
        (r.patient_id, r.trial_id, r.criterion_id): r for r in audit
    }
    matches: list[PatientTrialMatch] = []
    for patient in data.patients:
        for trial in data.trials:
            matches.append(match_patient_trial(data, patient.patient_id, trial.trial_id, audit_index))

    # Rank patients by score within each trial (descending).
    matches.sort(key=lambda m: (m.trial_id, -m.score, m.patient_id))
    return audit, matches
