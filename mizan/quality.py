"""Patient data quality gate (Prometheux patient_data_quality concept)."""

from __future__ import annotations

from dataclasses import dataclass

from mizan.loader import MizanData


@dataclass(frozen=True)
class PatientDataQuality:
    patient_id: str
    age: int
    sex: str
    city: str
    country: str
    diagnosis_value: str
    ecog_num: int
    missing_fields: str
    scoreable: str


def _has_diagnosis(data: MizanData, patient_id: str) -> str | None:
    for fact in data.patient_facts:
        if fact.patient_id == patient_id and fact.field_name == "diagnosis" and not fact.negated:
            return fact.str_value
    return None


def _has_ecog(data: MizanData, patient_id: str) -> int | None:
    for fact in data.patient_facts:
        if fact.patient_id == patient_id and fact.field_name == "ecog" and fact.num_value is not None:
            return int(fact.num_value)
    return None


def build_patient_data_quality(data: MizanData) -> list[PatientDataQuality]:
    """Mark each patient SCOREABLE or EXCLUDED MISSING DATA before matching."""
    rows: list[PatientDataQuality] = []
    for patient in data.patients:
        diag = _has_diagnosis(data, patient.patient_id)
        ecog = _has_ecog(data, patient.patient_id)

        if diag is not None and ecog is not None:
            rows.append(
                PatientDataQuality(
                    patient_id=patient.patient_id,
                    age=patient.age,
                    sex=patient.sex,
                    city=patient.city,
                    country=patient.country,
                    diagnosis_value=diag,
                    ecog_num=ecog,
                    missing_fields="none",
                    scoreable="YES",
                )
            )
        elif diag is None and ecog is not None:
            rows.append(
                PatientDataQuality(
                    patient_id=patient.patient_id,
                    age=patient.age,
                    sex=patient.sex,
                    city=patient.city,
                    country=patient.country,
                    diagnosis_value="MISSING",
                    ecog_num=ecog,
                    missing_fields="diagnosis",
                    scoreable="NO - EXCLUDED MISSING DATA",
                )
            )
        elif diag is not None and ecog is None:
            rows.append(
                PatientDataQuality(
                    patient_id=patient.patient_id,
                    age=patient.age,
                    sex=patient.sex,
                    city=patient.city,
                    country=patient.country,
                    diagnosis_value=diag,
                    ecog_num=-1,
                    missing_fields="ecog",
                    scoreable="NO - EXCLUDED MISSING DATA",
                )
            )
        else:
            rows.append(
                PatientDataQuality(
                    patient_id=patient.patient_id,
                    age=patient.age,
                    sex=patient.sex,
                    city=patient.city,
                    country=patient.country,
                    diagnosis_value="MISSING",
                    ecog_num=-1,
                    missing_fields="diagnosis,ecog",
                    scoreable="NO - EXCLUDED MISSING DATA",
                )
            )
    return rows
