"""HTTP API for Mizan — serves the Mizan-2 API.md contract to the frontend.

Thin FastAPI layer over the deterministic matching engine (mizan/ package).
Endpoints and response shapes follow API.md and the committed samples/ fixtures.
"""

from __future__ import annotations

import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mizan.dashboards import at_risk_trials, diagnosis_summary, trial_summaries
from mizan.evaluator import evaluate_criterion
from mizan.loader import FILE_ALIASES, MizanData, load_mizan_data
from mizan.matcher import (
    MatchTier,
    PairAssessmentDetail,
    assess_pair_detail,
    build_audit_trail,
)

DEFAULT_DATA_DIR = os.environ.get("MIZAN_DATA_DIR", "data")


class ApiError(Exception):
    """Raised to produce the API.md error envelope."""

    def __init__(self, status_code: int, code: str, message: str, details: list[str] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


class MizanState:
    """In-memory dataset plus lazily-cached derived views."""

    def __init__(self) -> None:
        self.data: MizanData | None = None
        self.data_dir: str = DEFAULT_DATA_DIR
        self._matches: list[PairAssessmentDetail] | None = None
        self._audit: list[dict[str, Any]] | None = None

    def load(self, data_dir: str) -> None:
        self.data = load_mizan_data(data_dir)
        self.data_dir = data_dir
        self._invalidate()

    def ensure_loaded(self) -> MizanData:
        if self.data is None:
            self.load(self.data_dir)
        assert self.data is not None
        return self.data

    def _invalidate(self) -> None:
        self._matches = None
        self._audit = None

    def refresh(self) -> None:
        """Recompute derived views from the current dataset."""
        self._invalidate()
        self.matches()
        self.audit()

    def active_trials(self) -> list[str]:
        data = self.ensure_loaded()
        with_rules = {c.trial_id for c in data.eligibility_criteria}
        return [t.trial_id for t in data.trials if t.status == "recruiting" and t.trial_id in with_rules]

    def matches(self) -> list[PairAssessmentDetail]:
        if self._matches is None:
            data = self.ensure_loaded()
            active = self.active_trials()
            rows: list[PairAssessmentDetail] = []
            for patient in data.patients:
                for trial_id in active:
                    detail = assess_pair_detail(data, patient.patient_id, trial_id)
                    if detail is not None:
                        rows.append(detail)
            rows.sort(key=lambda m: (m.trial_id, -m.score, m.patient_id))
            self._matches = rows
        return self._matches

    def audit(self) -> list[dict[str, Any]]:
        if self._audit is None:
            data = self.ensure_loaded()
            self._audit = [asdict(r) for r in build_audit_trail(data, self.active_trials())]
        return self._audit


STATE = MizanState()


# --------------------------------------------------------------------------- #
# Serialization helpers (shapes match API.md + samples/)
# --------------------------------------------------------------------------- #

def _serialize_match(detail: PairAssessmentDetail) -> dict[str, Any]:
    return {
        "patient_id": detail.patient_id,
        "trial_id": detail.trial_id,
        "trial_title": detail.trial_title,
        "tier": detail.tier.value,
        "score": detail.score,
        "soft_rules_met": detail.soft_rules_met,
        "soft_rules_total": detail.soft_rules_total,
        "soft_rules_unknown": detail.soft_rules_unknown,
        "location_bonus": detail.location_bonus,
        "hard_failures": detail.hard_failures,
        "hard_unknowns": detail.hard_unknowns,
        "soft_failures": detail.soft_failures,
    }


def _fact_num(num_value: float | None) -> Any:
    if num_value is None:
        return ""
    if float(num_value).is_integer():
        return float(num_value)
    return num_value


def _serialize_patient(patient) -> dict[str, Any]:
    return {
        "patient_id": patient.patient_id,
        "age": patient.age,
        "sex": patient.sex,
        "city": patient.city,
        "country": patient.country,
    }


def _serialize_fact(fact) -> dict[str, Any]:
    return {
        "patient_id": fact.patient_id,
        "fact_id": fact.fact_id,
        "field_name": fact.field_name,
        "num_value": _fact_num(fact.num_value),
        "str_value": fact.str_value,
        "unit": fact.unit,
        "negated": fact.negated,
        "confidence": fact.confidence,
        "source": fact.source,
    }


def _serialize_trial(trial) -> dict[str, Any]:
    return {
        "trial_id": trial.trial_id,
        "title": trial.title,
        "phase": trial.phase,
        "sponsor": trial.sponsor,
        "therapeutic_area": trial.therapeutic_area,
        "status": trial.status,
        "enrollment_count": trial.enrollment_count,
        "target_enrollment": trial.target_enrollment,
    }


def _serialize_criterion(criterion) -> dict[str, Any]:
    return {
        "criterion_id": criterion.criterion_id,
        "trial_id": criterion.trial_id,
        "rule_type": criterion.rule_type,
        "sequence_num": criterion.sequence_num,
        "field_checked": criterion.field_checked,
        "operator": criterion.operator,
        "value": criterion.value,
        "unit": "",
        "time_window": "",
        "notes": "",
        "hard_gate": criterion.hard_gate,
        "criterion_text": criterion.criterion_text,
    }


def _serialize_site(site) -> dict[str, Any]:
    return {
        "site_id": site.site_id,
        "trial_id": site.trial_id,
        "site_name": site.site_name,
        "city": site.city,
        "country": site.country,
    }


def _patient_info(data: MizanData, patient, criterion) -> str:
    field = criterion.field_checked
    if field.lower() == "age":
        return f"age={patient.age}"
    facts = [
        f for f in data.patient_facts
        if f.patient_id == patient.patient_id and f.field_name == field
    ]
    if not facts:
        return f"{field}=none"
    parts: list[str] = []
    for f in facts:
        if f.str_value:
            value = f.str_value
        elif f.num_value is not None:
            value = str(int(f.num_value)) if float(f.num_value).is_integer() else str(f.num_value)
        else:
            value = ""
        prefix = "not " if f.negated else ""
        token = f"{prefix}{value}".strip()
        if token:
            parts.append(token)
    return f"{field}={', '.join(parts) if parts else 'none'}"


def _pair_audit(data: MizanData, patient_id: str, trial_id: str) -> list[dict[str, Any]]:
    patient = next((p for p in data.patients if p.patient_id == patient_id), None)
    if patient is None:
        return []
    records: list[dict[str, Any]] = []
    for criterion in data.eligibility_criteria:
        if criterion.trial_id != trial_id:
            continue
        outcome = evaluate_criterion(data, patient_id, criterion)
        if outcome is None:
            continue
        records.append(
            {
                "patient_id": patient_id,
                "trial_id": trial_id,
                "criterion_id": criterion.criterion_id,
                "field_checked": criterion.field_checked,
                "rule_type": criterion.rule_type,
                "hard_gate": criterion.hard_gate,
                "result": outcome.result.value,
                "reason": outcome.reason,
                "patient_info": _patient_info(data, patient, criterion),
                "criterion_text": criterion.criterion_text or outcome.source_text,
            }
        )
    return records


def _coordinator_dashboard(data: MizanData, matches: list[PairAssessmentDetail]) -> list[dict[str, Any]]:
    summaries = {s.trial_id: s for s in trial_summaries(_as_match_lite(matches))}
    rows: list[dict[str, Any]] = []
    for trial in at_risk_trials(data):
        summary = summaries.get(trial.trial_id)
        rows.append(
            {
                "trial_id": trial.trial_id,
                "title": trial.title,
                "therapeutic_area": trial.therapeutic_area,
                "phase": trial.phase,
                "sponsor": trial.sponsor,
                "enrollment_count": trial.enrollment_count,
                "target_enrollment": trial.target_enrollment,
                "shortfall": trial.shortfall,
                "fill_pct": trial.fill_pct,
                "eligible_count": summary.eligible_count if summary else 0,
                "needs_screening_count": summary.needs_screening_count if summary else 0,
                "review_count": summary.review_count if summary else 0,
            }
        )
    return rows


class _MatchLite:
    """Adapter so dashboards.trial_summaries can consume PairAssessmentDetail."""

    __slots__ = ("patient_id", "trial_id", "trial_title", "tier")

    def __init__(self, detail: PairAssessmentDetail) -> None:
        self.patient_id = detail.patient_id
        self.trial_id = detail.trial_id
        self.trial_title = detail.trial_title
        self.tier = detail.tier


def _as_match_lite(matches: list[PairAssessmentDetail]) -> list[Any]:
    return [_MatchLite(m) for m in matches]


# --------------------------------------------------------------------------- #
# App factory
# --------------------------------------------------------------------------- #

def create_app() -> FastAPI:
    app = FastAPI(title="Mizan API", version="1.0.0")

    origins_env = os.environ.get("MIZAN_CORS_ORIGINS", "").strip()
    origins = [o.strip() for o in origins_env.split(",") if o.strip()] if origins_env else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ApiError)
    async def _api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            f"{'.'.join(str(p) for p in err.get('loc', []))}: {err.get('msg', '')}".strip(": ")
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": details,
                }
            },
        )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/patients")
    def get_patients() -> list[dict[str, Any]]:
        data = STATE.ensure_loaded()
        return [_serialize_patient(p) for p in data.patients]

    @app.get("/api/patients/{patient_id}")
    def get_patient(patient_id: str) -> dict[str, Any]:
        data = STATE.ensure_loaded()
        patient = next((p for p in data.patients if p.patient_id == patient_id), None)
        if patient is None:
            raise ApiError(404, "NOT_FOUND", f"Patient {patient_id} not found")
        facts = [_serialize_fact(f) for f in data.patient_facts if f.patient_id == patient_id]
        return {"patient": _serialize_patient(patient), "facts": facts}

    @app.get("/api/trials")
    def get_trials() -> list[dict[str, Any]]:
        data = STATE.ensure_loaded()
        return [_serialize_trial(t) for t in data.trials]

    @app.get("/api/trials/{trial_id}")
    def get_trial(trial_id: str) -> dict[str, Any]:
        data = STATE.ensure_loaded()
        trial = next((t for t in data.trials if t.trial_id == trial_id), None)
        if trial is None:
            raise ApiError(404, "NOT_FOUND", f"Trial {trial_id} not found")
        criteria = [
            _serialize_criterion(c) for c in data.eligibility_criteria if c.trial_id == trial_id
        ]
        sites = [_serialize_site(s) for s in data.sites if s.trial_id == trial_id]
        return {"trial": _serialize_trial(trial), "criteria": criteria, "sites": sites}

    @app.get("/api/matches")
    def get_matches(
        patient_id: str | None = Query(default=None),
        trial_id: str | None = Query(default=None),
        tier: str | None = Query(default=None),
    ) -> list[dict[str, Any]]:
        rows = STATE.matches()
        if patient_id:
            rows = [m for m in rows if m.patient_id == patient_id]
        if trial_id:
            rows = [m for m in rows if m.trial_id == trial_id]
        if tier:
            tier_upper = tier.upper()
            valid = {t.value for t in MatchTier}
            if tier_upper not in valid:
                raise ApiError(
                    400,
                    "VALIDATION_ERROR",
                    f"Invalid tier '{tier}'",
                    [f"Expected one of: {', '.join(sorted(valid))}"],
                )
            rows = [m for m in rows if m.tier.value == tier_upper]
        return [_serialize_match(m) for m in rows]

    @app.get("/api/matches/{patient_id}/{trial_id}")
    def get_match(patient_id: str, trial_id: str) -> dict[str, Any]:
        data = STATE.ensure_loaded()
        detail = assess_pair_detail(data, patient_id, trial_id)
        if detail is None:
            raise ApiError(404, "NOT_FOUND", f"No match for {patient_id}/{trial_id}")
        return _serialize_match(detail)

    @app.get("/api/matches/{patient_id}/{trial_id}/audit")
    def get_audit(patient_id: str, trial_id: str) -> list[dict[str, Any]]:
        data = STATE.ensure_loaded()
        return _pair_audit(data, patient_id, trial_id)

    @app.get("/api/dashboard/coordinator")
    def dashboard_coordinator() -> list[dict[str, Any]]:
        data = STATE.ensure_loaded()
        return _coordinator_dashboard(data, STATE.matches())

    @app.get("/api/dashboard/at-risk-trials")
    def dashboard_at_risk() -> list[dict[str, Any]]:
        data = STATE.ensure_loaded()
        return [asdict(r) for r in at_risk_trials(data)]

    @app.get("/api/dashboard/trial-summary")
    def dashboard_trial_summary() -> list[dict[str, Any]]:
        return [asdict(r) for r in trial_summaries(_as_match_lite(STATE.matches()))]

    @app.get("/api/dashboard/diagnosis-summary")
    def dashboard_diagnosis_summary() -> list[dict[str, Any]]:
        data = STATE.ensure_loaded()
        rows = diagnosis_summary(data, _as_match_lite(STATE.matches()))
        return [
            {"diagnosis": r.diagnosis, "eligible_patient_count": r.eligible_patient_count}
            for r in rows
        ]

    @app.post("/api/match/run")
    def match_run() -> dict[str, Any]:
        start = time.perf_counter()
        STATE.refresh()
        duration_ms = int((time.perf_counter() - start) * 1000)
        run_id = "run_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return {
            "status": "completed",
            "run_id": run_id,
            "duration_ms": duration_ms,
            "output_row_counts": {
                "audit_trail": len(STATE.audit()),
                "patient_trial_matches": len(STATE.matches()),
            },
        }

    @app.post("/api/import")
    async def import_data(
        patients: UploadFile = File(...),
        patient_facts: UploadFile = File(...),
        eligibility_criteria: UploadFile = File(...),
        trials: UploadFile = File(...),
        sites: UploadFile = File(...),
    ) -> dict[str, Any]:
        uploads = {
            "patients": patients,
            "patient_facts": patient_facts,
            "eligibility_criteria": eligibility_criteria,
            "trials": trials,
            "sites": sites,
        }
        tmp = Path(mkdtemp(prefix="mizan_import_"))
        for logical, upload in uploads.items():
            target_name = FILE_ALIASES[logical][0]
            content = await upload.read()
            (tmp / target_name).write_bytes(content)
        try:
            STATE.load(str(tmp))
            STATE.refresh()
        except (ValueError, FileNotFoundError) as exc:
            raise ApiError(400, "VALIDATION_ERROR", str(exc)) from exc

        data = STATE.ensure_loaded()
        return {
            "status": "ok",
            "message": "Data imported and matching completed",
            "inputs": {
                "patients": len(data.patients),
                "patient_facts": len(data.patient_facts),
                "eligibility_criteria": len(data.eligibility_criteria),
                "trials": len(data.trials),
                "sites": len(data.sites),
            },
            "output_row_counts": {
                "audit_trail": len(STATE.audit()),
                "patient_trial_matches": len(STATE.matches()),
            },
        }

    return app


app = create_app()
