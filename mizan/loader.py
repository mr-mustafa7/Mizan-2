"""Load and normalize Mizan input CSV files."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Accept common file name variants (user uploads vs Prometheux exports).
FILE_ALIASES: dict[str, list[str]] = {
    "patients": ["patients.csv", "patient.csv", "patient_csv.csv"],
    "patient_facts": ["patient_facts.csv", "patient_fact.csv", "patient_fact_csv.csv"],
    "eligibility_criteria": [
        "eligibility_criteria.csv",
        "eligibility_criterion.csv",
        "eligibility_criterion_csv.csv",
    ],
    "trials": ["trials.csv", "clinical_trial.csv", "clinical_trial_csv.csv"],
    "sites": ["sites.csv", "site.csv", "site_csv.csv"],
}


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace(" ", "_")


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "t", "1", "yes", "y"}:
        return True
    if text in {"false", "f", "0", "no", "n", ""}:
        return False
    raise ValueError(f"Cannot parse boolean: {value!r}")


def _parse_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "na", "n/a"}:
        return None
    return float(text)


def _parse_optional_int(value: Any) -> int | None:
    parsed = _parse_optional_float(value)
    return None if parsed is None else int(parsed)


@dataclass
class Patient:
    patient_id: str
    age: int
    sex: str
    city: str
    country: str


@dataclass
class PatientFact:
    patient_id: str
    fact_id: str
    field_name: str
    num_value: float | None
    str_value: str
    unit: str
    negated: bool
    confidence: str
    source: str


@dataclass
class EligibilityCriterion:
    criterion_id: str
    trial_id: str
    rule_type: str  # inclusion | exclusion
    field_checked: str
    operator: str
    value: str
    hard_gate: bool
    criterion_text: str
    sequence_num: str = ""


@dataclass
class Trial:
    trial_id: str
    title: str
    phase: str
    sponsor: str
    therapeutic_area: str
    status: str
    enrollment_count: int
    target_enrollment: int


@dataclass
class Site:
    site_id: str
    trial_id: str
    site_name: str
    city: str
    country: str


@dataclass
class MizanData:
    patients: list[Patient] = field(default_factory=list)
    patient_facts: list[PatientFact] = field(default_factory=list)
    eligibility_criteria: list[EligibilityCriterion] = field(default_factory=list)
    trials: list[Trial] = field(default_factory=list)
    sites: list[Site] = field(default_factory=list)
    source_paths: dict[str, Path] = field(default_factory=dict)


def _resolve_file(data_dir: Path, logical_name: str) -> Path:
    for candidate in FILE_ALIASES[logical_name]:
        path = data_dir / candidate
        if path.exists():
            return path
    names = ", ".join(FILE_ALIASES[logical_name])
    raise FileNotFoundError(
        f"Missing {logical_name} file in {data_dir}. Expected one of: {names}"
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header row")
        rows: list[dict[str, str]] = []
        for row in reader:
            normalized = {_normalize_key(k): (v or "").strip() for k, v in row.items()}
            rows.append(normalized)
        return rows


def _first(row: dict[str, str], *keys: str, default: str = "") -> str:
    for key in keys:
        norm = _normalize_key(key)
        if norm in row and row[norm] != "":
            return row[norm]
    return default


def load_mizan_data(data_dir: str | Path) -> MizanData:
    """Load all five Mizan CSV inputs from a directory."""
    base = Path(data_dir)
    if not base.is_dir():
        raise FileNotFoundError(f"Data directory does not exist: {base}")

    patients_path = _resolve_file(base, "patients")
    facts_path = _resolve_file(base, "patient_facts")
    criteria_path = _resolve_file(base, "eligibility_criteria")
    trials_path = _resolve_file(base, "trials")
    sites_path = _resolve_file(base, "sites")

    data = MizanData(
        source_paths={
            "patients": patients_path,
            "patient_facts": facts_path,
            "eligibility_criteria": criteria_path,
            "trials": trials_path,
            "sites": sites_path,
        }
    )

    for row in _read_csv(patients_path):
        age = _parse_optional_int(_first(row, "age"))
        if age is None:
            raise ValueError(f"Patient {_first(row, 'patient_id')} missing age")
        data.patients.append(
            Patient(
                patient_id=_first(row, "patient_id", "id"),
                age=age,
                sex=_first(row, "sex", "gender"),
                city=_first(row, "city"),
                country=_first(row, "country"),
            )
        )

    for row in _read_csv(facts_path):
        data.patient_facts.append(
            PatientFact(
                patient_id=_first(row, "patient_id", "id"),
                fact_id=_first(row, "fact_id", "id"),
                field_name=_first(row, "field_name", "field"),
                num_value=_parse_optional_float(_first(row, "num_value", "numeric_value")),
                str_value=_first(row, "str_value", "string_value", "value"),
                unit=_first(row, "unit"),
                negated=_parse_bool(_first(row, "negated", default="false")),
                confidence=_first(row, "confidence", default="unknown"),
                source=_first(row, "source", "source_document"),
            )
        )

    for row in _read_csv(criteria_path):
        hard_raw = _first(row, "hard_gate", "hard", "must_have")
        data.eligibility_criteria.append(
            EligibilityCriterion(
                criterion_id=_first(row, "criterion_id", "id"),
                trial_id=_first(row, "trial_id"),
                rule_type=_first(row, "rule_type", "type").lower(),
                field_checked=_first(row, "field_checked", "field"),
                operator=_first(row, "operator", "op"),
                value=_first(row, "value", "threshold"),
                hard_gate=_parse_bool(hard_raw if hard_raw else "true"),
                criterion_text=_first(
                    row, "criterion_text", "rule_text", "description", "original_rule"
                ),
                sequence_num=_first(row, "sequence_num", "criterion_number", "order"),
            )
        )

    for row in _read_csv(trials_path):
        enrollment = _parse_optional_int(_first(row, "enrollment_count", "enrolled", "enrollment"))
        target = _parse_optional_int(
            _first(row, "target_enrollment", "target", "enrollment_target")
        )
        if enrollment is None or target is None:
            raise ValueError(f"Trial {_first(row, 'trial_id')} missing enrollment fields")
        data.trials.append(
            Trial(
                trial_id=_first(row, "trial_id", "id"),
                title=_first(row, "title", "trial_title", "name"),
                phase=_first(row, "phase"),
                sponsor=_first(row, "sponsor"),
                therapeutic_area=_first(row, "therapeutic_area", "area", "indication"),
                status=_first(row, "status").lower(),
                enrollment_count=enrollment,
                target_enrollment=target,
            )
        )

    for row in _read_csv(sites_path):
        data.sites.append(
            Site(
                site_id=_first(row, "site_id", "id"),
                trial_id=_first(row, "trial_id"),
                site_name=_first(row, "site_name", "name"),
                city=_first(row, "city"),
                country=_first(row, "country"),
            )
        )

    return data


def summarize_inputs(data: MizanData) -> dict[str, Any]:
    """Return input file paths and row counts for validation output."""
    return {
        "files": {k: str(v) for k, v in data.source_paths.items()},
        "row_counts": {
            "patients": len(data.patients),
            "patient_facts": len(data.patient_facts),
            "eligibility_criteria": len(data.eligibility_criteria),
            "trials": len(data.trials),
            "sites": len(data.sites),
        },
        "columns_read": _read_columns(data),
    }


def _read_columns(data: MizanData) -> dict[str, list[str]]:
    columns: dict[str, list[str]] = {}
    for logical_name, path in data.source_paths.items():
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            columns[logical_name] = list(reader.fieldnames or [])
    return columns
