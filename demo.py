#!/usr/bin/env python3
"""Mizan foundation demo — five-layer clinical trial matching."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _discover_data_dir(explicit: str | None) -> Path:
    candidates = [Path(explicit)] if explicit else []
    candidates.extend([Path("data"), Path("/workspace/data"), Path(".")])
    from mizan.loader import FILE_ALIASES

    for directory in candidates:
        if not directory.is_dir():
            continue
        names = {p.name for p in directory.iterdir()}
        if all(any(alias in names for alias in FILE_ALIASES[key]) for key in FILE_ALIASES):
            return directory
    raise FileNotFoundError("Place the five CSV files in ./data/")


def _print_architecture() -> None:
    from mizan.architecture import FOUNDATION_REFERENCES, LAYER_DESCRIPTIONS, Layer

    print("Mizan Foundation Architecture (medtech decision-support demo)\n")
    print("Five layers — no LLM/GPU required:\n")
    for layer in Layer:
        print(f"  {layer.value}  {LAYER_DESCRIPTIONS[layer]}")
    print("\nResearch basis:\n")
    for ref in FOUNDATION_REFERENCES:
        print(f"  • {ref.title}")
        print(f"    {ref.source} → {ref.maps_to}")
        print(f"    {ref.url}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Mizan foundation demo")
    parser.add_argument("--data-dir", help="Input CSV directory (default: ./data)")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--show-architecture", action="store_true", help="Print layer map and exit")
    args = parser.parse_args()

    if args.show_architecture:
        _print_architecture()
        return 0

    try:
        data_dir = _discover_data_dir(args.data_dir)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    from mizan.pipeline import run_pipeline

    report = run_pipeline(data_dir, args.output_dir)
    demo = json.loads((Path(args.output_dir) / "demo_summary.json").read_text())

    print("=" * 60)
    print("  MIZAN — Clinical Trial Matching Demo")
    print("=" * 60)
    print()
    for layer in report["layers"]:
        print(f"  [{layer['id']}] {layer['description']}")
        print(f"           → {layer['artifact']} ({layer['row_count']} rows)")
    print()
    print("Key demo metrics:")
    print(f"  Patients:                  {demo['patients']}")
    print(f"  Recruiting trials matched: {demo['recruiting_trials_evaluated']}")
    print(f"  At-risk trials:            {demo['at_risk_trials']}")
    print(f"  Needs screening (recruit):   {demo['needs_screening_highlight']}")
    if demo.get("top_shortfall_trial"):
        t = demo["top_shortfall_trial"]
        print(f"  Biggest shortfall:         {t['title']} ({t['shortfall']} patients needed)")
    print()
    print("Tier breakdown:")
    for tier, count in demo["tier_counts"].items():
        print(f"  {tier}: {count}")
    print()
    checks = report["logic_checks"]
    print(f"Logic checks: {'PASSED' if checks['passed'] else 'FAILED'}")
    print(f"\nOpen {args.output_dir}/coordinator_dashboard.csv for the coordinator view")
    print(f"Open {args.output_dir}/patient_shortlists.csv for per-patient top-20 trials")
    return 0 if checks["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
