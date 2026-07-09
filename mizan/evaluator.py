"""Evaluate eligibility criteria (Prometheux criterion_evaluation concept)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mizan.loader import EligibilityCriterion, MizanData, Patient


class CriterionResult(str, Enum):
    MET = "MET"
    NOT_MET = "NOT_MET"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class EvaluationOutcome:
    result: CriterionResult
    reason: str
    source_text: str


def _contains(haystack: str, needle: str) -> bool:
    return needle.lower() in haystack.lower()


def _facts(data: MizanData, patient_id: str, field: str):
    return [f for f in data.patient_facts if f.patient_id == patient_id and f.field_name == field]


def _patient(data: MizanData, patient_id: str) -> Patient | None:
    for p in data.patients:
        if p.patient_id == patient_id:
            return p
    return None


def _source_text(criterion: EligibilityCriterion) -> str:
    return criterion.source_text or criterion.criterion_text or (
        f"{criterion.rule_type} {criterion.field_checked} {criterion.operator} {criterion.value}"
    )


def is_supported_criterion(criterion: EligibilityCriterion) -> bool:
    """Only rule combinations defined in Prometheux criterion_evaluation."""
    field = criterion.field_checked.lower()
    op = criterion.operator.lower()
    pol = criterion.rule_type.lower()
    if field == "age" and pol == "inclusion" and op in ("ge", "le"):
        return True
    if field == "ecog" and pol == "inclusion" and op == "le":
        return True
    if field == "diagnosis" and pol == "inclusion" and op == "contains":
        return True
    if field == "cancer_stage" and pol == "inclusion" and op == "contains":
        return True
    if field.startswith("biomarker_") and op == "positive" and pol in ("inclusion", "exclusion"):
        return True
    if field == "prior_treatments" and op == "contains" and pol in ("inclusion", "exclusion"):
        return True
    return False


def _has_ecog(data: MizanData, patient_id: str) -> bool:
    return any(f.num_value is not None for f in _facts(data, patient_id, "ecog"))


def _has_diag(data: MizanData, patient_id: str) -> bool:
    return any(not f.negated and f.str_value for f in _facts(data, patient_id, "diagnosis"))


def _has_stage(data: MizanData, patient_id: str) -> bool:
    return bool(_facts(data, patient_id, "cancer_stage"))


def _has_marker(data: MizanData, patient_id: str, field: str) -> bool:
    return bool(_facts(data, patient_id, field))


def _has_prior_any(data: MizanData, patient_id: str) -> bool:
    return bool(_facts(data, patient_id, "prior_treatments"))


def _has_prior_real(data: MizanData, patient_id: str) -> bool:
    return any(f.str_value.strip().lower() != "none" for f in _facts(data, patient_id, "prior_treatments"))


def _excluded_hit(data: MizanData, patient_id: str, value: str) -> bool:
    for f in _facts(data, patient_id, "prior_treatments"):
        if f.str_value.strip().lower() != "none" and _contains(f.str_value, value):
            return True
    return False


def _included_hit(data: MizanData, patient_id: str, value: str) -> bool:
    for f in _facts(data, patient_id, "prior_treatments"):
        if f.str_value.strip().lower() != "none" and _contains(f.str_value, value):
            return True
    return False


def evaluate_criterion(
    data: MizanData, patient_id: str, criterion: EligibilityCriterion
) -> EvaluationOutcome | None:
    """Evaluate one criterion; returns None if not in Vadalog spec."""
    if not is_supported_criterion(criterion):
        return None

    patient = _patient(data, patient_id)
    if patient is None:
        return EvaluationOutcome(CriterionResult.UNKNOWN, "Patient not found", _source_text(criterion))

    src = _source_text(criterion)
    field = criterion.field_checked.lower()
    op = criterion.operator.lower()
    pol = criterion.rule_type.lower()

    # ---------- AGE ----------
    if field == "age":
        threshold = int(float(criterion.value))
        if op == "ge":
            if patient.age >= threshold:
                return EvaluationOutcome(CriterionResult.MET, f"Age {patient.age} meets minimum {threshold}", src)
            return EvaluationOutcome(CriterionResult.NOT_MET, f"Age {patient.age} below minimum {threshold}", src)
        if op == "le":
            if patient.age <= threshold:
                return EvaluationOutcome(CriterionResult.MET, f"Age {patient.age} meets maximum {threshold}", src)
            return EvaluationOutcome(CriterionResult.NOT_MET, f"Age {patient.age} exceeds maximum {threshold}", src)

    # ---------- ECOG ----------
    if field == "ecog":
        if not _has_ecog(data, patient_id):
            return EvaluationOutcome(
                CriterionResult.UNKNOWN, "No ECOG performance status on record", src
            )
        ecog_val = next(f.num_value for f in _facts(data, patient_id, "ecog") if f.num_value is not None)
        threshold = int(float(criterion.value))
        ecog_int = int(ecog_val)
        if ecog_val <= threshold:
            return EvaluationOutcome(CriterionResult.MET, f"ECOG {ecog_int} within limit {threshold}", src)
        return EvaluationOutcome(CriterionResult.NOT_MET, f"ECOG {ecog_int} exceeds limit {threshold}", src)

    # ---------- DIAGNOSIS ----------
    if field == "diagnosis":
        if not _has_diag(data, patient_id):
            return EvaluationOutcome(CriterionResult.UNKNOWN, "No diagnosis on record", src)
        diag = next(
            f.str_value for f in _facts(data, patient_id, "diagnosis") if not f.negated and f.str_value
        )
        val = criterion.value
        if _contains(diag, val) or _contains(val, diag):
            return EvaluationOutcome(CriterionResult.MET, f"Diagnosis '{diag}' matches required '{val}'", src)
        return EvaluationOutcome(CriterionResult.NOT_MET, f"Diagnosis '{diag}' does not match required '{val}'", src)

    # ---------- CANCER STAGE ----------
    if field == "cancer_stage":
        if not _has_stage(data, patient_id):
            return EvaluationOutcome(CriterionResult.UNKNOWN, "No cancer stage on record", src)
        stage = next(f.str_value for f in _facts(data, patient_id, "cancer_stage") if f.str_value)
        if _contains(stage, criterion.value):
            return EvaluationOutcome(CriterionResult.MET, f"Cancer stage '{stage}' matches '{criterion.value}'", src)
        return EvaluationOutcome(CriterionResult.NOT_MET, f"Cancer stage '{stage}' does not match '{criterion.value}'", src)

    # ---------- BIOMARKER positive ----------
    if field.startswith("biomarker_") and op == "positive":
        marker = field[len("biomarker_"):].upper() or field.upper()
        if not _has_marker(data, patient_id, field):
            return EvaluationOutcome(
                CriterionResult.UNKNOWN, f"No {marker} result on record", src
            )
        facts = _facts(data, patient_id, field)
        if pol == "inclusion":
            for f in facts:
                if f.negated:
                    return EvaluationOutcome(
                        CriterionResult.NOT_MET, f"{marker} explicitly absent - fails inclusion", src
                    )
            for f in facts:
                if not f.negated:
                    sv = f.str_value.strip().lower()
                    if sv == "wild type":
                        return EvaluationOutcome(
                            CriterionResult.NOT_MET, f"{marker} wild type - fails inclusion", src
                        )
                    if sv == "negative":
                        return EvaluationOutcome(
                            CriterionResult.NOT_MET, f"{marker} negative - fails inclusion", src
                        )
                    if sv == "not detected":
                        return EvaluationOutcome(
                            CriterionResult.NOT_MET, f"{marker} not detected - fails inclusion", src
                        )
                    if sv and sv not in {"wild type", "negative", "not detected"}:
                        return EvaluationOutcome(
                            CriterionResult.MET, f"{marker} '{f.str_value}' positive - meets inclusion", src
                        )
            return EvaluationOutcome(CriterionResult.UNKNOWN, f"No {marker} result on record", src)

        # exclusion
        for f in facts:
            if f.negated:
                return EvaluationOutcome(CriterionResult.MET, f"{marker} absent - passes exclusion", src)
        for f in facts:
            if not f.negated:
                sv = f.str_value.strip().lower()
                if sv in {"wild type", "negative", "not detected"}:
                    return EvaluationOutcome(CriterionResult.MET, f"{marker} {sv} - passes exclusion", src)
                if sv and sv not in {"wild type", "negative", "not detected"}:
                    return EvaluationOutcome(CriterionResult.NOT_MET, f"{marker} '{f.str_value}' positive - fails exclusion", src)
        return EvaluationOutcome(CriterionResult.UNKNOWN, f"No {marker} result on record", src)

    # ---------- PRIOR TREATMENTS ----------
    if field == "prior_treatments":
        val = criterion.value
        if pol == "exclusion":
            if not _has_prior_any(data, patient_id):
                return EvaluationOutcome(
                    CriterionResult.UNKNOWN, "No treatment history on record", src
                )
            if not _has_prior_real(data, patient_id):
                return EvaluationOutcome(CriterionResult.MET, "Treatment-naive - passes exclusion", src)
            if _excluded_hit(data, patient_id, val):
                return EvaluationOutcome(CriterionResult.NOT_MET, f"Prior '{val}' found - fails exclusion", src)
            return EvaluationOutcome(
                CriterionResult.MET, f"Excluded treatment '{val}' not found - passes", src
            )

        # inclusion
        if not _has_prior_any(data, patient_id):
            return EvaluationOutcome(
                CriterionResult.UNKNOWN, "No treatment history on record", src
            )
        if _included_hit(data, patient_id, val):
            return EvaluationOutcome(CriterionResult.MET, f"Required prior '{val}' found", src)
        return EvaluationOutcome(CriterionResult.NOT_MET, f"Required prior '{val}' not found", src)

    return None


def unsupported_reason(criterion: EligibilityCriterion) -> str:
    """Human-readable reason a criterion is outside the Vadalog evaluator scope."""
    field = criterion.field_checked.lower()
    op = criterion.operator.lower()
    pol = criterion.rule_type.lower()
    if field == "age" and pol == "exclusion":
        return "age exclusion not modelled in criterion_evaluation"
    if field == "ecog" and (op != "le" or pol != "inclusion"):
        return "only ecog/le inclusion is modelled"
    if field.startswith("lab_") or field in {
        "hemoglobin",
        "platelet_count",
        "anc",
        "creatinine",
        "bilirubin",
        "alt",
        "ast",
    }:
        return "lab thresholds not modelled in criterion_evaluation"
    if field == "sex":
        return "sex criteria not modelled in criterion_evaluation"
    return f"no evaluator for field '{criterion.field_checked}' / {op} / {pol}"


def build_criterion_evaluation(
    data: MizanData, trial_ids: list[str] | None = None
) -> list[tuple[EligibilityCriterion, str, EvaluationOutcome]]:
    """One row per patient × trial × supported criterion."""
    active_trials = set(trial_ids) if trial_ids else {t.trial_id for t in data.trials}
    rows: list[tuple[EligibilityCriterion, str, EvaluationOutcome]] = []
    for patient in data.patients:
        for criterion in data.eligibility_criteria:
            if criterion.trial_id not in active_trials:
                continue
            if not is_supported_criterion(criterion):
                continue
            outcome = evaluate_criterion(data, patient.patient_id, criterion)
            if outcome is not None:
                rows.append((criterion, patient.patient_id, outcome))
    return rows
