# Mizan API Contract

Shared contract between the **Mizan backend** (`mr-mustafa7/Mizan-2`, branch `cursor/clinical-trial-matching-e8ea`) and the **Mizan frontend** (separate repo).

Mizan helps clinical trial coordinators match patients to trials with a full audit trail: every recommendation shows which criteria passed, failed, or need more screening.

## Conventions

| Topic | Rule |
|-------|------|
| Base URL (local) | `http://localhost:8000` |
| Base URL (prod) | Set by backend deploy, e.g. `https://mizan-api.onrender.com` |
| Content-Type | `application/json` for all responses except file upload |
| Field names | `snake_case` (matches Python dataclasses) |
| CORS | Backend must allow frontend origin (localhost + production URL) |

### Enums

```ts
type MatchTier = 'ELIGIBLE' | 'NEEDS_SCREENING' | 'REVIEW' | 'NOT_ELIGIBLE';
type CriterionResult = 'MET' | 'NOT_MET' | 'UNKNOWN' | 'NOT_APPLICABLE';
type RuleType = 'inclusion' | 'exclusion';
```

### Error shape (all non-2xx)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable summary",
    "details": ["Optional detail lines"]
  }
}
```

Sample: [`samples/error-response.json`](samples/error-response.json)

---

## Endpoint status

| Endpoint | Status | Sample response |
|----------|--------|-----------------|
| `POST /api/import` | 🔴 Not started | [`samples/import-response.json`](samples/import-response.json) |
| `POST /api/match/run` | 🔴 Not started | [`samples/match-run-response.json`](samples/match-run-response.json) |
| `GET /api/matches` | 🔴 Not started | [`samples/matches.json`](samples/matches.json) |
| `GET /api/matches/{patient_id}/{trial_id}` | 🔴 Not started | (single `PatientTrialMatch` from matches list) |
| `GET /api/matches/{patient_id}/{trial_id}/audit` | 🔴 Not started | [`samples/audit-trail-P001-NCT001.json`](samples/audit-trail-P001-NCT001.json) |
| `GET /api/patients` | 🔴 Not started | [`samples/patients.json`](samples/patients.json) |
| `GET /api/patients/{patient_id}` | 🔴 Not started | [`samples/patient-P001.json`](samples/patient-P001.json) |
| `GET /api/trials` | 🔴 Not started | [`samples/trials.json`](samples/trials.json) |
| `GET /api/trials/{trial_id}` | 🔴 Not started | [`samples/trial-NCT001.json`](samples/trial-NCT001.json) |
| `GET /api/dashboard/coordinator` | 🔴 Not started | [`samples/coordinator-dashboard.json`](samples/coordinator-dashboard.json) |
| `GET /api/dashboard/at-risk-trials` | 🔴 Not started | [`samples/at-risk-trials.json`](samples/at-risk-trials.json) |
| `GET /api/dashboard/trial-summary` | 🔴 Not started | [`samples/trial-summary.json`](samples/trial-summary.json) |
| `GET /api/dashboard/diagnosis-summary` | 🔴 Not started | [`samples/diagnosis-summary.json`](samples/diagnosis-summary.json) |
| `GET /api/health` | 🔴 Not started | `{ "status": "ok" }` |

Update the status column as endpoints are implemented: 🔴 not started → 🟡 stub → 🟢 ready.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-09 | Initial contract + sample JSON from matching pipeline |

---

## `GET /api/health`

Liveness check for deploy and frontend connection testing.

**Response 200**

```json
{ "status": "ok" }
```

---

## `POST /api/import`

Upload the five Mizan input CSV files, load them, and run the matching pipeline.

**Content-Type:** `multipart/form-data`

**Form fields** (each value is a file; backend accepts filename aliases per loader):

| Field | Accepted filenames |
|-------|-------------------|
| `patients` | `patients.csv`, `patient.csv` |
| `patient_facts` | `patient_facts.csv`, `patient_fact.csv` |
| `eligibility_criteria` | `eligibility_criteria.csv`, `eligibility_criterion.csv` |
| `trials` | `trials.csv`, `clinical_trial.csv` |
| `sites` | `sites.csv`, `site.csv` |

**Response 200:** [`samples/import-response.json`](samples/import-response.json)

**Response 400:** [`samples/error-response.json`](samples/error-response.json)

---

## `POST /api/match/run`

Re-run matching on already-imported data (no file upload).

**Request body:** optional `{}`

**Response 200:** [`samples/match-run-response.json`](samples/match-run-response.json)

---

## `GET /api/matches`

List patient–trial match results.

**Query parameters** (all optional):

| Param | Type | Example |
|-------|------|---------|
| `patient_id` | string | `P001` |
| `trial_id` | string | `NCT001` |
| `tier` | MatchTier | `ELIGIBLE` |

**Response 200:** `PatientTrialMatch[]` — see [`samples/matches.json`](samples/matches.json)

### `PatientTrialMatch`

| Field | Type | Description |
|-------|------|-------------|
| `patient_id` | string | |
| `trial_id` | string | |
| `trial_title` | string | |
| `tier` | MatchTier | Overall classification |
| `score` | number | Composite score (includes location bonus when eligible) |
| `soft_rules_met` | number | |
| `soft_rules_total` | number | |
| `soft_rules_unknown` | number | |
| `location_bonus` | number | City/country proximity bonus |
| `hard_failures` | number | |
| `hard_unknowns` | number | |
| `soft_failures` | number | |

---

## `GET /api/matches/{patient_id}/{trial_id}`

Single match summary for a patient–trial pair.

**Response 200:** one `PatientTrialMatch` object.

**Response 404:** no match row for this pair.

---

## `GET /api/matches/{patient_id}/{trial_id}/audit`

**Core explainability endpoint.** One row per eligibility criterion evaluated for this pair.

**Response 200:** `AuditRecord[]` — see [`samples/audit-trail-P001-NCT001.json`](samples/audit-trail-P001-NCT001.json)

### `AuditRecord`

| Field | Type | Description |
|-------|------|-------------|
| `patient_id` | string | |
| `trial_id` | string | |
| `criterion_id` | string | |
| `field_checked` | string | e.g. `diagnosis`, `age`, `ecog` |
| `rule_type` | RuleType | `inclusion` or `exclusion` |
| `hard_gate` | boolean | Hard gate vs soft rule |
| `result` | CriterionResult | `MET`, `NOT_MET`, `UNKNOWN`, `NOT_APPLICABLE` |
| `reason` | string | Human-readable evaluation reason |
| `patient_info` | string | Source data used in evaluation |
| `criterion_text` | string | Original criterion wording |

**UI guidance:** group rows by `hard_gate`, sort by `rule_type` (inclusion first), show `result` + `reason` prominently.

---

## `GET /api/patients`

**Response 200:** `Patient[]` — see [`samples/patients.json`](samples/patients.json)

### `Patient`

| Field | Type |
|-------|------|
| `patient_id` | string |
| `age` | number |
| `sex` | string |
| `city` | string |
| `country` | string |

---

## `GET /api/patients/{patient_id}`

Patient demographics plus structured clinical facts.

**Response 200:** see [`samples/patient-P001.json`](samples/patient-P001.json)

```json
{
  "patient": { "patient_id": "P001", "age": 67, "sex": "F", "city": "Boston", "country": "USA" },
  "facts": [ /* PatientFact[] */ ]
}
```

### `PatientFact`

| Field | Type |
|-------|------|
| `patient_id` | string |
| `fact_id` | string |
| `field_name` | string |
| `num_value` | number \| null |
| `str_value` | string |
| `unit` | string |
| `negated` | boolean |
| `confidence` | string |
| `source` | string |

---

## `GET /api/trials`

**Response 200:** `Trial[]` — see [`samples/trials.json`](samples/trials.json)

### `Trial`

| Field | Type |
|-------|------|
| `trial_id` | string |
| `title` | string |
| `phase` | string |
| `sponsor` | string |
| `therapeutic_area` | string |
| `status` | string |
| `enrollment_count` | number |
| `target_enrollment` | number |

---

## `GET /api/trials/{trial_id}`

Trial metadata, eligibility criteria, and sites.

**Response 200:** see [`samples/trial-NCT001.json`](samples/trial-NCT001.json)

```json
{
  "trial": { /* Trial */ },
  "criteria": [ /* EligibilityCriterion[] */ ],
  "sites": [ /* Site[] */ ]
}
```

### `EligibilityCriterion`

| Field | Type |
|-------|------|
| `criterion_id` | string |
| `trial_id` | string |
| `rule_type` | RuleType |
| `sequence_num` | string |
| `field_checked` | string |
| `operator` | string |
| `value` | string |
| `hard_gate` | boolean |
| `criterion_text` | string |

### `Site`

| Field | Type |
|-------|------|
| `site_id` | string |
| `trial_id` | string |
| `site_name` | string |
| `city` | string |
| `country` | string |

---

## Dashboard endpoints

Aggregated views produced by the matching pipeline (`mizan/dashboards.py`).

### `GET /api/dashboard/coordinator`

At-risk recruiting trials with patient tier counts.

**Response 200:** [`samples/coordinator-dashboard.json`](samples/coordinator-dashboard.json)

### `GET /api/dashboard/at-risk-trials`

Trials below 50% enrollment target.

**Response 200:** [`samples/at-risk-trials.json`](samples/at-risk-trials.json)

### `GET /api/dashboard/trial-summary`

Per-trial counts of patients in each match tier.

**Response 200:** [`samples/trial-summary.json`](samples/trial-summary.json)

### `GET /api/dashboard/diagnosis-summary`

Distinct eligible patients grouped by diagnosis.

**Response 200:** [`samples/diagnosis-summary.json`](samples/diagnosis-summary.json)

---

## CORS (backend requirement)

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://<your-frontend-domain>",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Frontend integration

```bash
# .env.local
VITE_API_URL=http://localhost:8000
VITE_USE_MOCKS=true   # use public/mocks copied from samples/ until API is ready
```

Point `VITE_USE_MOCKS=false` and set `VITE_API_URL` to the deployed backend URL at integration time.

---

## Sample data source

All files in [`samples/`](samples/) were generated from the Mizan matching pipeline on branch `cursor/clinical-trial-matching-e8ea` using the bundled `data/` CSVs. Backend implementations should return JSON matching these shapes.
