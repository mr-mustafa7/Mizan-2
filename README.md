# Mizan AI

Clinical trial matching for cancer coordinators — foundation architecture for medtech demos.

## Quick demo

```bash
python3 demo.py
```

```bash
python3 demo.py --show-architecture   # print the five-layer map
```

Outputs land in `output/`: `patient_data_quality.csv`, `pair_assessment.csv`, `audit_trail.csv`,
`rejection_reason.csv`, `criterion_coverage.csv` (which criteria were evaluated vs dropped),
`coordinator_dashboard.csv`, `trial_summary.csv`, `diagnosis_summary.csv`, `patient_shortlists.csv`,
and `demo_summary.json`.

> **Coverage transparency:** the Python engine only evaluates the field/operator/polarity
> combinations defined in `prometheux/mizan.vada`. Any other criterion (e.g. lab thresholds,
> age exclusions) is reported in `criterion_coverage.csv` as `evaluated=NO` with a reason — never
> silently ignored.

## Foundation architecture

Five layers, aligned with published clinical trial matching research but kept simple (no LLM/GPU):

| Layer | Purpose | Research basis |
|-------|---------|----------------|
| **1. Ingest** | Load patients, facts, criteria, trials, sites | Structured cohort model (WIDE / MatchMiner style) |
| **2. Prefilter** | Recruiting trials with rules only | TrialMatchAI deterministic pre-filters (age, status) |
| **3. Eligibility** | `MET` / `NOT_MET` / `UNKNOWN` per criterion (`criterion_evaluation`) | Prometheux Vadalog; ICH GCP audit trail |
| **4. Ranking** | Soft-rule % + location bonus → tier (`pair_assessment`) | Prometheux Vadalog tiers |
| **5. Decision support** | At-risk trials, shortlists, coordinator dashboard | TrialMatchAI top-20 review window (WIDE study) |

### Research references

- [TrialMatchAI (Nature Communications, 2026)](https://doi.org/10.1038/s41467-026-70509-w) — criterion-level eligibility, top-K shortlists, decision support
- [MatchMiner (npj Precision Oncology, 2022)](https://doi.org/10.1038/s41598-022-23225-3) — deterministic structured rules
- ICH E6(R3) GCP — traceable eligibility audit trail

## Data inputs

Place five CSV files in `data/` or Prometheux-style `disk/`:

- `patients.csv` / `patient.csv` — patient_id, age, sex, city, country
- `patient_facts.csv` — diagnosis, biomarkers, labs, ECOG, prior treatments
- `eligibility_criteria.csv` — inclusion/exclusion rules per trial
- `trials.csv` — enrollment counts, status, phase
- `sites.csv` — trial locations

## Project layout

```
mizan/
  architecture.py   # Layer definitions + research citations
  stages.py         # Five pipeline stages
  loader.py         # CSV ingest
  evaluator.py      # criterion_evaluation + criterion coverage (Prometheux Vadalog)
  matcher.py        # pair_assessment tiers, audit trail, rejection reasons
  quality.py        # patient_data_quality gate
  dashboards.py     # Coordinator views
  pipeline.py       # Orchestrator
demo.py             # Demo runner
data/               # Sample cohort
disk/               # Prometheux-named CSV inputs
prometheux/         # Authoritative mizan.vada Vadalog spec
output/             # Generated artifacts
```

## What this is / isn't

**Is:** A deterministic decision-support foundation you can demo to coordinators and extend later with retrieval or NLP.

**Isn't:** An autonomous enrollment system or a medical device. All matches require human review.

## Prometheux + Cursor (MCP plugin)

This cloud agent **cannot** use your local MCP plugins. Connect Prometheux on **Cursor Desktop** (your machine):

### 1. Install

```bash
pip install pipx && pipx ensurepath && pipx install prometheux-mcp
which prometheux-mcp
```

### 2. Put credentials here

Copy `.cursor/mcp.json.example` → `.cursor/mcp.json` (or `~/.cursor/mcp.json` for all projects):

```json
{
  "mcpServers": {
    "prometheux": {
      "command": "/full/path/to/prometheux-mcp",
      "args": ["--url", "https://api.prometheux.ai"],
      "env": {
        "PROMETHEUX_TOKEN": "your_token_here",
        "PROMETHEUX_USERNAME": "your_username",
        "PROMETHEUX_ORGANIZATION": "your_organization"
      }
    }
  }
}
```

Get token/username/org from **Prometheux account settings**. `.cursor/mcp.json` is gitignored — never commit it.

### 3. Enable

**Cursor Settings** → **Tools & MCP** → toggle **prometheux** on → open a **new chat**.

Guide: https://docs.prometheux.ai/integrations/mcp/cursor
