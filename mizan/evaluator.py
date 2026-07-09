"""Evaluate individual eligibility criteria against patient data."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from mizan.loader import EligibilityCriterion, MizanData, Patient, PatientFact

NEGATIVE_MARKERS = {
    "wild type",
    "wild-type",
    "wt",
    "negative",
    "not detected",
    "not_detected",
    "undetected",
    "absent",
    "none detected",
    "no mutation",
}

LUNG_DIAGNOSIS_KEYWORDS = ("lung", "nsclc", "sclc", "pulmonary", "bronch")
BREAST_DIAGNOSIS_KEYWORDS = ("breast", "mammary")
COLORECTAL_DIAGNOSIS_KEYWORDS = ("colorectal", "colon", "rectal", "crc")


class CriterionResult(str, Enum):
    MET = "MET"
    NOT_MET = "NOT_MET"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class EvaluationOutcome:
    result: CriterionResult
    reason: str
    patient_info: str


def _contains(haystack: str, needle: str) -> bool:
    return needle.lower() in haystack.lower()


def _facts_for_field(data: MizanData, patient_id: str, field_name: str) -> list[PatientFact]:
    return [f for f in data.patient_facts if f.patient_id == patient_id and f.field_name == field_name]


def _patient(data: MizanData, patient_id: str) -> Patient | None:
    for patient in data.patients:
        if patient.patient_id == patient_id:
            return patient
    return None


def _diagnosis(data: MizanData, patient_id: str) -> str | None:
    for fact in _facts_for_field(data, patient_id, "diagnosis"):
        if not fact.negated and fact.str_value:
            return fact.str_value
    return None


def _is_negative_marker(fact: PatientFact) -> bool:
    if fact.negated:
        return True
    value = fact.str_value.strip().lower()
    return value in NEGATIVE_MARKERS


def _fact_display(fact: PatientFact | None, fallback: str = "") -> str:
    if fact is None:
        return fallback or "no recorded value"
    parts = [f"field={fact.field_name}"]
    if fact.num_value is not None:
        parts.append(f"num_value={fact.num_value}")
    if fact.str_value:
        parts.append(f"str_value={fact.str_value}")
    if fact.negated:
        parts.append("negated=true")
    if fact.confidence:
        parts.append(f"confidence={fact.confidence}")
    return ", ".join(parts)


def _best_fact(facts: list[PatientFact]) -> PatientFact | None:
    if not facts:
        return None
    # Prefer non-negated facts with highest confidence wording.
    ranked = sorted(
        facts,
        key=lambda f: (
            f.negated,
            f.confidence.lower() not in {"high", "confirmed", "definite"},
            not f.str_value and f.num_value is None,
        ),
    )
    return ranked[0]


def _inclusion_outcome(
    satisfied: bool | None, reason_met: str, reason_not_met: str, patient_info: str
) -> EvaluationOutcome:
    if satisfied is None:
        return EvaluationOutcome(CriterionResult.UNKNOWN, "Insufficient patient data to evaluate", patient_info)
    if satisfied:
        return EvaluationOutcome(CriterionResult.MET, reason_met, patient_info)
    return EvaluationOutcome(CriterionResult.NOT_MET, reason_not_met, patient_info)


def _exclusion_outcome(
    triggered: bool | None, reason_met: str, reason_not_met: str, patient_info: str
) -> EvaluationOutcome:
    """For exclusion rules, MET means the patient is NOT excluded (passes)."""
    if triggered is None:
        return EvaluationOutcome(CriterionResult.UNKNOWN, "Insufficient patient data to evaluate", patient_info)
    if triggered:
        return EvaluationOutcome(CriterionResult.NOT_MET, reason_not_met, patient_info)
    return EvaluationOutcome(CriterionResult.MET, reason_met, patient_info)


def _biomarker_not_applicable(diagnosis: str | None, field: str) -> bool:
    if not diagnosis:
        return False
    diag = diagnosis.lower()
    field_lower = field.lower()
    if "egfr" in field_lower or "alk" in field_lower or "kras" in field_lower:
        return not any(token in diag for token in LUNG_DIAGNOSIS_KEYWORDS)
    if "her2" in field_lower or "er_status" in field_lower or "pr_status" in field_lower:
        return not any(token in diag for token in BREAST_DIAGNOSIS_KEYWORDS)
    if "braf" in field_lower and "colorectal" not in diag and "melanoma" not in diag:
        if any(token in diag for token in COLORECTAL_DIAGNOSIS_KEYWORDS):
            return False
        return "melanoma" not in diag
    return False


def _evaluate_age(
    data: MizanData, patient: Patient, criterion: EligibilityCriterion
) -> EvaluationOutcome:
    info = f"age={patient.age}"
    threshold = int(float(criterion.value))
    if criterion.operator == "ge":
        satisfied = patient.age >= threshold
        return _inclusion_outcome(
            satisfied,
            f"Age {patient.age} meets minimum {threshold}",
            f"Age {patient.age} is below minimum {threshold}",
            info,
        )
    if criterion.operator == "le":
        satisfied = patient.age <= threshold
        return _inclusion_outcome(
            satisfied,
            f"Age {patient.age} meets maximum {threshold}",
            f"Age {patient.age} exceeds maximum {threshold}",
            info,
        )
    return EvaluationOutcome(
        CriterionResult.UNKNOWN,
        f"Unsupported age operator '{criterion.operator}'",
        info,
    )


def _evaluate_ecog(data: MizanData, patient_id: str, criterion: EligibilityCriterion) -> EvaluationOutcome:
    facts = _facts_for_field(data, patient_id, "ecog")
    fact = _best_fact(facts)
    if fact is None or fact.num_value is None:
        return EvaluationOutcome(CriterionResult.UNKNOWN, "No ECOG performance status recorded", "ecog=missing")
    info = _fact_display(fact)
    threshold = int(float(criterion.value))
    if criterion.operator == "le":
        satisfied = fact.num_value <= threshold
        return _inclusion_outcome(
            satisfied,
            f"ECOG {int(fact.num_value)} is within limit {threshold}",
            f"ECOG {int(fact.num_value)} exceeds limit {threshold}",
            info,
        )
    if criterion.operator == "ge":
        satisfied = fact.num_value >= threshold
        return _inclusion_outcome(
            satisfied,
            f"ECOG {int(fact.num_value)} meets minimum {threshold}",
            f"ECOG {int(fact.num_value)} is below minimum {threshold}",
            info,
        )
    return EvaluationOutcome(
        CriterionResult.UNKNOWN,
        f"Unsupported ECOG operator '{criterion.operator}'",
        info,
    )


def _evaluate_diagnosis(data: MizanData, patient_id: str, criterion: EligibilityCriterion) -> EvaluationOutcome:
    diagnosis = _diagnosis(data, patient_id)
    if diagnosis is None:
        return EvaluationOutcome(CriterionResult.UNKNOWN, "No diagnosis recorded for patient", "diagnosis=missing")
    info = f"diagnosis={diagnosis}"
    needle = criterion.value
    satisfied = _contains(diagnosis, needle) or _contains(needle, diagnosis)
    return _inclusion_outcome(
        satisfied,
        f"Diagnosis '{diagnosis}' matches required '{needle}'",
        f"Diagnosis '{diagnosis}' does not match required '{needle}'",
        info,
    )


def _evaluate_cancer_stage(data: MizanData, patient_id: str, criterion: EligibilityCriterion) -> EvaluationOutcome:
    facts = _facts_for_field(data, patient_id, "cancer_stage")
    fact = _best_fact(facts)
    if fact is None or not fact.str_value or fact.str_value.lower() in {"unknown", "not assessed"}:
        return EvaluationOutcome(CriterionResult.UNKNOWN, "No cancer stage recorded", "cancer_stage=missing")
    stage = fact.str_value
    info = _fact_display(fact)
    if criterion.operator == "contains":
        satisfied = _contains(stage, criterion.value)
        return _inclusion_outcome(
            satisfied,
            f"Cancer stage '{stage}' contains required '{criterion.value}'",
            f"Cancer stage '{stage}' does not contain required '{criterion.value}'",
            info,
        )
    return EvaluationOutcome(
        CriterionResult.UNKNOWN,
        f"Unsupported cancer_stage operator '{criterion.operator}'",
        info,
    )


def _evaluate_biomarker(data: MizanData, patient_id: str, criterion: EligibilityCriterion) -> EvaluationOutcome:
    field = criterion.field_checked
    diagnosis = _diagnosis(data, patient_id)
    if _biomarker_not_applicable(diagnosis, field):
        return EvaluationOutcome(
            CriterionResult.NOT_APPLICABLE,
            f"Biomarker rule for {field} does not apply to diagnosis '{diagnosis}'",
            f"diagnosis={diagnosis}",
        )

    facts = _facts_for_field(data, patient_id, field)
    fact = _best_fact(facts)
    if fact is None:
        return EvaluationOutcome(
            CriterionResult.UNKNOWN,
            f"No {field} result available",
            f"{field}=missing",
        )

    info = _fact_display(fact)
    is_negative = _is_negative_marker(fact)
    is_positive = not is_negative and bool(fact.str_value.strip())

    if criterion.operator == "positive":
        if criterion.rule_type == "inclusion":
            if is_positive:
                return EvaluationOutcome(
                    CriterionResult.MET,
                    f"{field} is positive/mutated as required",
                    info,
                )
            if is_negative:
                return EvaluationOutcome(
                    CriterionResult.NOT_MET,
                    f"{field} is negative/wild type but trial requires positive status",
                    info,
                )
            return EvaluationOutcome(CriterionResult.UNKNOWN, f"{field} result is inconclusive", info)

        # exclusion: patient must NOT be positive
        if is_positive:
            return EvaluationOutcome(
                CriterionResult.NOT_MET,
                f"{field} is positive/mutated and patient is excluded",
                info,
            )
        if is_negative:
            return EvaluationOutcome(
                CriterionResult.MET,
                f"{field} is negative/wild type — passes exclusion",
                info,
            )
        return EvaluationOutcome(CriterionResult.UNKNOWN, f"{field} result is inconclusive", info)

    if criterion.operator == "negative":
        if is_negative:
            return EvaluationOutcome(CriterionResult.MET, f"{field} is negative as required", info)
        if is_positive:
            return EvaluationOutcome(
                CriterionResult.NOT_MET,
                f"{field} is positive but trial requires negative status",
                info,
            )
        return EvaluationOutcome(CriterionResult.UNKNOWN, f"{field} result is inconclusive", info)

    return EvaluationOutcome(
        CriterionResult.UNKNOWN,
        f"Unsupported biomarker operator '{criterion.operator}'",
        info,
    )


def _evaluate_prior_treatments(
    data: MizanData, patient_id: str, criterion: EligibilityCriterion
) -> EvaluationOutcome:
    facts = _facts_for_field(data, patient_id, "prior_treatments")
    fact = _best_fact(facts)
    needle = criterion.value
    if fact is None:
        if criterion.rule_type == "inclusion" and needle.lower() in {"none", "no prior treatment"}:
            return EvaluationOutcome(
                CriterionResult.UNKNOWN,
                "Prior treatment history not recorded — cannot confirm treatment-naive status",
                "prior_treatments=missing",
            )
        return EvaluationOutcome(
            CriterionResult.UNKNOWN,
            "Prior treatment history not recorded",
            "prior_treatments=missing",
        )

    treatments = fact.str_value.strip()
    info = _fact_display(fact)
    if treatments.lower() in {"none", "no prior treatment", "na", "n/a"}:
        treatments = "none"

    if criterion.rule_type == "exclusion":
        if treatments == "none":
            return EvaluationOutcome(
                CriterionResult.MET,
                "No prior treatments recorded — passes treatment exclusion",
                info,
            )
        triggered = _contains(treatments, needle)
        return _exclusion_outcome(
            triggered,
            f"Prior treatments '{treatments}' do not include excluded '{needle}'",
            f"Prior treatment '{treatments}' includes excluded '{needle}'",
            info,
        )

    # inclusion: must have required prior treatment
    needle = criterion.value
    if needle.lower() in {"none", "no prior treatment"}:
        if treatments == "none":
            return EvaluationOutcome(
                CriterionResult.MET,
                "Patient is treatment-naive as required",
                info,
            )
        return EvaluationOutcome(
            CriterionResult.NOT_MET,
            f"Patient has prior treatments '{treatments}' but trial prefers treatment-naive patients",
            info,
        )

    if treatments == "none":
        return EvaluationOutcome(
            CriterionResult.NOT_MET,
            f"Required prior treatment '{needle}' not found (patient has none)",
            info,
        )
    satisfied = _contains(treatments, needle)
    return _inclusion_outcome(
        satisfied,
        f"Required prior treatment '{needle}' found in '{treatments}'",
        f"Required prior treatment '{needle}' not found in '{treatments}'",
        info,
    )


def _evaluate_lab(data: MizanData, patient_id: str, criterion: EligibilityCriterion) -> EvaluationOutcome:
    field = criterion.field_checked
    facts = _facts_for_field(data, patient_id, field)
    fact = _best_fact(facts)
    if fact is None:
        return EvaluationOutcome(CriterionResult.UNKNOWN, f"No {field} lab result recorded", f"{field}=missing")

    value = fact.num_value
    if value is None:
        try:
            value = float(fact.str_value)
        except ValueError:
            return EvaluationOutcome(
                CriterionResult.UNKNOWN,
                f"{field} value is not numeric",
                _fact_display(fact),
            )

    info = _fact_display(fact)
    threshold = float(criterion.value)
    if criterion.operator == "ge":
        satisfied = value >= threshold
        return _inclusion_outcome(
            satisfied,
            f"{field} {value} meets minimum {threshold}",
            f"{field} {value} is below minimum {threshold}",
            info,
        )
    if criterion.operator == "le":
        satisfied = value <= threshold
        return _inclusion_outcome(
            satisfied,
            f"{field} {value} meets maximum {threshold}",
            f"{field} {value} exceeds maximum {threshold}",
            info,
        )
    return EvaluationOutcome(
        CriterionResult.UNKNOWN,
        f"Unsupported lab operator '{criterion.operator}'",
        info,
    )


def _evaluate_sex(patient: Patient, criterion: EligibilityCriterion) -> EvaluationOutcome:
    info = f"sex={patient.sex}"
    required = criterion.value.lower()
    actual = patient.sex.lower()
    satisfied = actual == required or (required in {"m", "male"} and actual in {"m", "male"}) or (
        required in {"f", "female"} and actual in {"f", "female"}
    )
    return _inclusion_outcome(
        satisfied,
        f"Patient sex '{patient.sex}' matches required '{criterion.value}'",
        f"Patient sex '{patient.sex}' does not match required '{criterion.value}'",
        info,
    )


FIELD_EVALUATORS: dict[str, Callable[..., EvaluationOutcome]] = {}


def _register_evaluators() -> None:
    FIELD_EVALUATORS.update(
        {
            "age": lambda data, patient, criterion, pid: _evaluate_age(data, patient, criterion),
            "sex": lambda data, patient, criterion, pid: _evaluate_sex(patient, criterion),
            "ecog": lambda data, patient, criterion, pid: _evaluate_ecog(data, pid, criterion),
            "diagnosis": lambda data, patient, criterion, pid: _evaluate_diagnosis(data, pid, criterion),
            "cancer_stage": lambda data, patient, criterion, pid: _evaluate_cancer_stage(data, pid, criterion),
            "prior_treatments": lambda data, patient, criterion, pid: _evaluate_prior_treatments(
                data, pid, criterion
            ),
        }
    )


_register_evaluators()


def evaluate_criterion(
    data: MizanData, patient_id: str, criterion: EligibilityCriterion
) -> EvaluationOutcome:
    """Evaluate one criterion for one patient."""
    patient = _patient(data, patient_id)
    if patient is None:
        return EvaluationOutcome(CriterionResult.UNKNOWN, "Patient not found", f"patient_id={patient_id}")

    field = criterion.field_checked.lower()

    if field in FIELD_EVALUATORS:
        outcome = FIELD_EVALUATORS[field](data, patient, criterion, patient_id)
    elif field.startswith("biomarker_") or field in {"her2", "alk", "braf", "kras", "pd_l1", "pd-l1"}:
        outcome = _evaluate_biomarker(data, patient_id, criterion)
    elif field.startswith("lab_") or field in {
        "hemoglobin",
        "platelet_count",
        "anc",
        "creatinine",
        "bilirubin",
        "alt",
        "ast",
    }:
        outcome = _evaluate_lab(data, patient_id, criterion)
    else:
        outcome = EvaluationOutcome(
            CriterionResult.UNKNOWN,
            f"No evaluator implemented for field '{criterion.field_checked}'",
            f"field={criterion.field_checked}",
        )

    # Flip semantics for exclusion rules: MET on inclusion logic becomes NOT_MET on exclusion.
    if criterion.rule_type == "exclusion" and field in {"age", "ecog", "diagnosis", "cancer_stage", "sex"}:
        if outcome.result == CriterionResult.MET:
            return EvaluationOutcome(
                CriterionResult.NOT_MET,
                f"Patient matches exclusion criterion: {outcome.reason}",
                outcome.patient_info,
            )
        if outcome.result == CriterionResult.NOT_MET:
            return EvaluationOutcome(
                CriterionResult.MET,
                f"Patient does not match exclusion: {outcome.reason}",
                outcome.patient_info,
            )

    return outcome
