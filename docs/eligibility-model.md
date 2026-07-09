# Mizan Eligibility Model — Hard Gates, Soft Gates, Tiers & Score

Integration reference for the frontend. Describes exactly how Mizan turns
per-criterion evaluations into a patient–trial tier and match score, and what
objects the UI consumes.

---

## 1. Hard gates vs soft gates

Every eligibility criterion carries a boolean **`hard_gate`** flag (from
`eligibility_criterion.csv`, column `hard_gate`).

| Type | `hard_gate` | Meaning |
|------|-------------|---------|
| **Hard gate** | `true` | *Mandatory.* A single hard-gate failure disqualifies the patient outright ("must be true to enroll"). E.g. required diagnosis, EGFR-mutation requirement, a triggered exclusion. |
| **Soft gate** | `false` | *Scoring/preference.* Failing it does **not** disqualify; it only lowers the match score and can move the tier from `ELIGIBLE` to `REVIEW`. E.g. "cancer stage documented", "adequate hemoglobin". |

Both hard and soft criteria are evaluated identically per criterion; only their
effect on the final decision differs.

---

## 2. Per-criterion result (`criterion_evaluation`)

Each patient × criterion produces one `result`:

| Result | Meaning |
|--------|---------|
| `MET` | Patient satisfies the rule |
| `NOT_MET` | Patient fails the rule |
| `UNKNOWN` | **Missing data** — never treated as a failure |

> **Core rule:** missing data → `UNKNOWN`, never `NOT_MET`. This lets an
> incomplete patient route to "needs screening" instead of being wrongly rejected.

Each row also carries the explanation/audit payload the UI should show per criterion:

| Field | Type | Notes |
|-------|------|-------|
| `criterion_id` | string | |
| `patient_id` | string | |
| `trial_id` | string | |
| `field_checked` | string | e.g. `age`, `ecog`, `diagnosis`, `biomarker_egfr` |
| `comparator` | string | e.g. `ge`, `le`, `contains`, `positive` |
| `polarity` | string | `inclusion` or `exclusion` |
| `hard_gate` | bool | mandatory vs scoring |
| `result` | enum | `MET` / `NOT_MET` / `UNKNOWN` |
| `reason` | string | plain-English explanation |
| `source_text` | string | original rule wording |

---

## 3. Tier decision (`pair_assessment`)

For a patient–trial pair, aggregate its criteria:

```
hard_fail    = any hard-gate criterion is NOT_MET
hard_unknown = any hard-gate criterion is UNKNOWN
soft_met     = count of soft criteria that are MET
soft_total   = count of soft criteria (evaluated)
```

Then assign the tier **in this priority order** (first match wins):

| Priority | Tier | Condition | Plain meaning |
|----------|------|-----------|---------------|
| 1 | `NOT_ELIGIBLE` | `hard_fail` | Any mandatory criterion failed. Hard failure dominates everything. |
| 2 | `NEEDS_SCREENING` | not `hard_fail` **and** `hard_unknown` | No hard failure, but mandatory data is missing → go collect it. |
| 3 | `ELIGIBLE` | all hard pass **and** `2 × soft_met ≥ soft_total` | All mandatory met and ≥ 50% of scoring criteria met. A trial with **zero** soft rules is ELIGIBLE (`0 ≥ 0`). |
| 4 | `REVIEW` | all hard pass **and** `2 × soft_met < soft_total` | Mandatory met, but < 50% of scoring criteria met → borderline. |

Reference implementation:

```144:156:mizan/matcher.py
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
```

---

## 4. Match score

```
soft_pct       = 100 * soft_met / soft_total   (integer division; 100 if soft_total == 0)
location_bonus = 25 if patient city  == a trial site city
                 15 else if patient country == a trial site country
                 0  otherwise
score          = soft_pct + location_bonus     (0 if NOT_ELIGIBLE)
```

- `location_bonus`: city match wins over country match; skipped entirely on hard failure.
- **`score` range: 0–125.** Max (125) = ELIGIBLE, all soft rules met, same-city site.
- `NOT_ELIGIBLE` always scores `0`.

Reference implementation:

```138:141:mizan/matcher.py
def _soft_pct(soft_met: int, soft_total: int) -> int:
    if soft_total == 0:
        return 100
    return (100 * soft_met) // soft_total
```

```236:239:mizan/matcher.py
    tier = _classify_pair(hard_fail, hard_unknown, soft_met, soft_total)
    loc_bonus = 0 if hard_fail else _location_bonus(data, patient, trial_id)
    pct = _soft_pct(soft_met, soft_total)
    score = 0.0 if hard_fail else float(pct + loc_bonus)
```

---

## 5. The object the frontend consumes (`pair_assessment` row)

One row per patient–trial pair (`output/pair_assessment.csv`):

| Field | Type | Notes |
|-------|------|-------|
| `patient_id` | string | |
| `trial_id` | string | |
| `trial_title` | string | |
| `tier` | enum | `ELIGIBLE` / `NEEDS_SCREENING` / `REVIEW` / `NOT_ELIGIBLE` |
| `score` | float | 0–125; 0 when `NOT_ELIGIBLE` |
| `soft_rules_met` | int | |
| `soft_rules_total` | int | |
| `location_bonus` | float | 0 / 15 / 25 |

To render the **why** behind a row, join to `criterion_evaluation` / `audit_trail`
on `(patient_id, trial_id)` and list each criterion with its `hard_gate`,
`result`, `reason`, and `source_text`.

Supporting outputs:

| File | Use in UI |
|------|-----------|
| `audit_trail.csv` | Per-criterion rows with patient demographics + `reason` + `rule_text` |
| `rejection_reason.csv` | For `NOT_ELIGIBLE`: exactly which hard gates were `NOT_MET` (decisive factors) |
| `criterion_coverage.csv` | Criteria the engine did **not** auto-evaluate (`evaluated = NO` + reason) — show as "manual check", never silently hidden |
| `patient_data_quality.csv` | Whether a patient is scoreable (diagnosis + ECOG present) or `EXCLUDED MISSING DATA` |

---

## 6. Suggested UI mapping

- **Tier → badge/color:** `ELIGIBLE` (green), `NEEDS_SCREENING` (amber, "collect data"), `REVIEW` (blue, "borderline"), `NOT_ELIGIBLE` (grey/red).
- **Split the criteria panel** into "Mandatory (hard gates)" and "Scoring (soft gates)". Within each, show `MET` ✓ / `NOT_MET` ✗ / `UNKNOWN` ？ with `reason` and `source_text`.
- **Decisive-factor highlight:**
  - `NOT_ELIGIBLE` → surface hard `NOT_MET` criteria (that's `rejection_reason.csv`).
  - `NEEDS_SCREENING` → surface hard `UNKNOWN` criteria (the data to collect).
- **Score bar:** show `soft_pct` + `location_bonus` breakdown so the number is explainable.
- **Coverage note:** display `criterion_coverage` `evaluated = NO` rows as "not auto-evaluated, manual check".

### Tier tooltips

- **ELIGIBLE** — "All mandatory criteria met; majority of scoring criteria met."
- **NEEDS_SCREENING** — "Mandatory criteria not violated, but data is missing — screen the patient to confirm."
- **REVIEW** — "Mandatory criteria met, but fewer than half the scoring criteria met — coordinator judgment needed."
- **NOT_ELIGIBLE** — "At least one mandatory criterion failed."

---

## 7. Match explanation object (`match_explanations.json`)

For the **"Why this patient was matched"** UI block, the backend emits one
explanation object per patient × trial pair. Generated by
`mizan/explanation.py` → `build_match_explanation(data, patient_id, trial_id)`
and written to `output/match_explanations.json`. Committed contract samples:
`docs/samples/match-explanation-P001-NCT001.json` (ELIGIBLE) and
`docs/samples/match-explanation-not-eligible.json`.

```jsonc
{
  "patient_id": "P001",
  "trial_id": "NCT001",
  "trial_title": "EGFR Inhibitor Study NSCLC",
  "tier": "ELIGIBLE",              // ELIGIBLE | NEEDS_SCREENING | REVIEW | NOT_ELIGIBLE
  "score": 125.0,                   // 0-125
  "soft_rules_met": 1,
  "soft_rules_total": 1,
  "location_bonus": 25.0,
  "summary": "P001 is ELIGIBLE for ...: all 6 mandatory criteria passed and 1 of 1 preference criteria met, with a +25 location bonus.",
  "highlights": ["6 of 6 hard gates passed", "+25 location bonus (same city ...)"],
  "decisive_factors": [],           // filled for NOT_ELIGIBLE (failed hard gates) and NEEDS_SCREENING (missing hard data)
  "facts": [                        // one per evaluated criterion -> a Fact Card
    {
      "field_checked": "diagnosis",
      "patient_value": "NSCLC adenocarcinoma",
      "result": "MET",             // MET | NOT_MET | UNKNOWN
      "bar": "green",              // green (MET) | amber (UNKNOWN) | red (NOT_MET)
      "hard_gate": true,
      "polarity": "inclusion",
      "criterion_id": "C001",
      "criterion_text": "Histologically confirmed NSCLC",
      "reason": "Diagnosis matches"
    }
  ],
  "steps": [                        // ordered, human-readable reasoning chain
    { "step": 1, "title": "Data quality gate", "detail": "..." },
    { "step": 2, "title": "Mandatory (hard) gates", "detail": "..." },
    { "step": 3, "title": "Decisive factor", "detail": "..." },
    { "step": 4, "title": "Preference scoring", "detail": "..." },
    { "step": 5, "title": "Tier assigned", "detail": "..." }
  ]
}
```

### Frontend field mapping

| UI element | Source field |
|------------|--------------|
| Tier badge + match score | `tier`, `score` |
| Fact card avatar / value | `facts[].field_checked`, `facts[].patient_value` |
| Fact match bar (green/amber/red) | `facts[].bar` (derived from `facts[].result`) |
| Fact criterion + reason | `facts[].criterion_text`, `facts[].reason` |
| "Why matched" summary | `summary` |
| Bullet highlights | `highlights` |
| Rejection / screening callout | `decisive_factors` |
| Step-by-step reasoning | `steps` |
| Link to full audit trail | join `audit_trail.csv` on `(patient_id, trial_id)` |

> Facts include age as a demographic fact whenever an age criterion is checked
> (P001 → both min and max age criteria), matching the frontend behavior.

---

## 8. Worked examples

Assume a trial with 4 hard inclusion criteria + 1 soft criterion, patient in the same city as a site.

| Scenario | Hard results | Soft | Tier | Score |
|----------|-------------|------|------|-------|
| Perfect match | all `MET` | 1/1 `MET` | `ELIGIBLE` | `100 + 25 = 125` |
| Missing biomarker | 3 `MET`, 1 `UNKNOWN` | 1/1 `MET` | `NEEDS_SCREENING` | `100 + 25 = 125` |
| Wrong diagnosis | 1 `NOT_MET` | — | `NOT_ELIGIBLE` | `0` |
| Passes hard, weak soft | all `MET` | 0/2 `MET` | `REVIEW` | `0 + 25 = 25` |

> Note: score is a ranking aid, not the tier. `NEEDS_SCREENING` can score high
> (missing data isn't penalized) — the tier tells the coordinator what action to take.
