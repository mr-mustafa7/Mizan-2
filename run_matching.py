#!/usr/bin/env python3
"""Run the Mizan AI clinical trial matching pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _discover_data_dir(explicit: str | None) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend(
        [
            Path("data"),
            Path("/workspace/data"),
            Path("/opt/cursor/artifacts/assets"),
            Path("."),
        ]
    )
    required_sets = [
        ["patients.csv", "patient_facts.csv", "eligibility_criteria.csv", "trials.csv", "sites.csv"],
        ["patient.csv", "patient_fact.csv", "eligibility_criterion.csv", "clinical_trial.csv", "site.csv"],
    ]
    for directory in candidates:
        if not directory.is_dir():
            continue
        names = {p.name for p in directory.iterdir()}
        for required in required_sets:
            if all(name in names for name in required):
                return directory
        # Partial match via loader aliases
        try:
            from mizan.loader import FILE_ALIASES

            if all(any(alias in names for alias in FILE_ALIASES[key]) for key in FILE_ALIASES):
                return directory
        except Exception:
            pass
    raise FileNotFoundError(
        "Could not find Mizan input CSVs. Place the five files in ./data/ "
        "(patients, patient_facts, eligibility_criteria, trials, sites)."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Mizan AI trial matching pipeline")
    parser.add_argument("--data-dir", help="Directory containing the five input CSV files")
    parser.add_argument("--output-dir", default="output", help="Directory for output CSVs")
    args = parser.parse_args()

    try:
        data_dir = _discover_data_dir(args.data_dir)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    from mizan.pipeline import run_pipeline

    report = run_pipeline(data_dir, args.output_dir)

    print("=== Mizan AI Matching Pipeline ===\n")
    print("Input files:")
    for key, path in report["inputs"]["files"].items():
        count = report["inputs"]["row_counts"][key]
        cols = report["inputs"]["columns_read"].get(key, [])
        print(f"  {key}: {path}")
        print(f"    rows={count}, columns={cols}")

    print("\nOutput row counts:")
    for name, count in report["output_row_counts"].items():
        print(f"  {name}: {count}")

    checks = report["logic_checks"]
    print(f"\nLogic checks: {'PASSED' if checks['passed'] else 'FAILED'}")
    for issue in checks["issues"]:
        print(f"  - {issue}")

    print(f"\nFull report: {Path(args.output_dir) / 'pipeline_report.json'}")
    return 0 if checks["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
