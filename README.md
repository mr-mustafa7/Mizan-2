# Mizan AI

Clinical trial matching for cancer coordinators — foundation architecture for medtech demos.

## Quick demo

```bash
python3 demo.py
```

```bash
python3 demo.py --show-architecture   # print the five-layer map
```

Outputs land in `output/` including `coordinator_dashboard.csv`, `patient_shortlists.csv`, and `demo_summary.json`.

## Foundation architecture

Five layers, aligned with published clinical trial matching research but kept simple (no LLM/GPU):

| Layer | Purpose | Research basis |
|-------|---------|----------------|
| **1. Ingest** | Load patients, facts, criteria, trials, sites | Structured cohort model (WIDE / MatchMiner style) |
| **2. Prefilter** | Recruiting trials with rules only | TrialMatchAI deterministic pre-filters (age, status) |
| **3. Eligibility** | MET / NOT MET / UNKNOWN / NOT APPLICABLE per criterion | TrialMatchAI criterion labels; ICH GCP audit trail |
| **4. Ranking** | Composite score `(S_inc + S_exc) / 2` + tier | TrialMatchAI Methods Eq. 1–2 |
| **5. Decision support** | At-risk trials, shortlists, coordinator dashboard | TrialMatchAI top-20 review window (WIDE study) |

### Research references

- [TrialMatchAI (Nature Communications, 2026)](https://doi.org/10.1038/s41467-026-70509-w) — criterion-level eligibility, top-K shortlists, decision support
- [MatchMiner (npj Precision Oncology, 2022)](https://doi.org/10.1038/s41598-022-23225-3) — deterministic structured rules
- ICH E6(R3) GCP — traceable eligibility audit trail

## Data inputs

Place five CSV files in `data/`:

- `patients.csv` — patient_id, age, sex, city, country
- `patient_facts.csv` — diagnosis, biomarkers, labs, ECOG, prior treatments
- `eligibility_criteria.csv` — inclusion/exclusion rules per trial
- `trials.csv` — enrollment counts, status, phase
- `sites.csv` — trial locations

## Project layout

```
mizan/
  architecture.py   # Layer definitions + research citations
  stages.py         # Five pipeline stages
  scoring.py        # Composite inclusion/exclusion score
  loader.py         # CSV ingest
  evaluator.py      # Criterion rules engine
  matcher.py        # Tiers + audit types
  dashboards.py     # Coordinator views
  pipeline.py       # Orchestrator
demo.py             # Demo runner
data/               # Sample cohort
output/             # Generated artifacts
```

## What this is / isn't

**Is:** A deterministic decision-support foundation you can demo to coordinators and extend later with retrieval or NLP.

**Isn't:** An autonomous enrollment system or a medical device. All matches require human review.
