# Prometheux Vadalog — Mizan

This folder contains the authoritative **Prometheux Vadalog** specification for Mizan clinical trial matching.

## Files

| File | Purpose |
|------|---------|
| `mizan.vada` | Full Vadalog program (all concepts) |
| `../disk/*.csv` | Input CSVs (`patient.csv`, `patient_fact.csv`, etc.) |

## Concepts (execution order)

1. **patient_data_quality** — Scoreable gate (diagnosis + ECOG required)
2. **at_risk_trial** — Recruiting trials under 50% enrolled
3. **criterion_evaluation** — Single source of truth (`MET` / `NOT_MET` / `UNKNOWN`)
4. **pair_assessment** — Patient–trial tiers and match scores
5. **audit_trail** — GCP view derived from `criterion_evaluation`
6. **rejection_reason** — Hard-gate failures for `NOT_ELIGIBLE` pairs
7. **trial_summary** / **coordinator_dashboard** / **diagnosis_summary** — Coordinator views

Legacy concepts (`criterion_detail`, `gate_evaluation`) remain in the Vadalog for backward compatibility but are superseded by `criterion_evaluation` + `pair_assessment`.

## Python parity

The `mizan/` package implements `criterion_evaluation` and `pair_assessment` logic in Python for local demo runs without a Prometheux connection.

## Prometheux MCP (desktop)

Configure in `.cursor/mcp.json` (see `.cursor/mcp.json.example`):

```json
{
  "mcpServers": {
    "prometheux": {
      "command": "prometheux-mcp",
      "env": {
        "PROMETHEUX_TOKEN": "...",
        "PROMETHEUX_USERNAME": "...",
        "PROMETHEUX_ORGANIZATION": "..."
      }
    }
  }
}
```

Run the program in Prometheux with `disk/` as the data root.
