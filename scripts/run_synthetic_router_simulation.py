#!/usr/bin/env python3
"""Write deterministic synthetic router benchmark artifacts locally only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from night_shift_pilot.simulation import benchmark, markdown_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/router-simulation-v0.2"))
    args = parser.parse_args()
    report = benchmark()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "report.md").write_text(markdown_report(report), encoding="utf-8")
    print(f"synthetic router report written to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
