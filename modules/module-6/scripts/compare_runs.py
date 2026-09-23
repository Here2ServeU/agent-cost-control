#!/usr/bin/env python3
"""MODULE 6 - DID ROUTING SAVE MONEY, AND DID ANYTHING GET WORSE?

    python3 compare_runs.py --before baseline --after routed

Two batches of runs, compared on cost AND on quality. Routing is the
only change in this course that can make answers worse, so a saving on
its own proves nothing. If quality moved at all, put that step back on
the expensive model: the saving is not worth an argument about quality.
"""
from __future__ import annotations

import argparse
import sys

import ledger


def stats(batch: str) -> dict | None:
    runs = [r for r in ledger.read_runs() if r.get("batch") == batch and r["result"] != "refused"]
    if not runs:
        return None
    spend = sum(r["cost_usd"] for r in runs)
    ok = sum(1 for r in runs if r["result"] == "success")
    correct = sum(1 for r in runs if r.get("correct"))
    routed = sorted({s for r in runs for s in r.get("routed", [])})
    return {"runs": len(runs), "spend": spend, "per_run": spend / len(runs),
            "per_success": spend / ok if ok else None,
            "success_rate": ok / len(runs), "correct_rate": correct / len(runs),
            "routed": ", ".join(routed) or "nothing"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare two batches on cost and quality.")
    ap.add_argument("--before", required=True, help="batch name, e.g. baseline")
    ap.add_argument("--after", required=True, help="batch name, e.g. routed")
    a = ap.parse_args()

    b, r = stats(a.before), stats(a.after)
    for name, s in ((a.before, b), (a.after, r)):
        if s is None:
            print(f"No runs in batch '{name}'. Run: python3 run_agent.py --input samples/normal.json "
                  f"--repeat 20 --batch {name} --quiet")
            return 1

    def ps(x: float | None) -> str:
        return "undefined" if x is None else f"${x:.4f}"

    print()
    print(f"  {'':<24}{a.before:>20}{a.after:>20}")
    print("  " + "-" * 64)
    print(f"  {'routed to cheap model':<24}{b['routed']:>20}{r['routed']:>20}")
    print(f"  {'runs':<24}{b['runs']:>20}{r['runs']:>20}")
    print(f"  {'cost per run':<24}{ps(b['per_run']):>20}{ps(r['per_run']):>20}")
    print(f"  {'cost per success':<24}{ps(b['per_success']):>20}{ps(r['per_success']):>20}")
    print(f"  {'passed the check':<24}{b['success_rate']:>20.0%}{r['success_rate']:>20.0%}")
    print(f"  {'right answer':<24}{b['correct_rate']:>20.0%}{r['correct_rate']:>20.0%}")
    print("  " + "-" * 64)

    saving = (1 - r["per_run"] / b["per_run"]) * 100
    quality_moved = r["correct_rate"] < b["correct_rate"] or r["success_rate"] < b["success_rate"]
    print(f"  saving per run          {saving:.0f}%")
    if quality_moved:
        print("  quality                 WORSE. Put that step back on the expensive model.")
    else:
        print("  quality                 unchanged. Keep the routing, and keep watching it.")
    print()
    return 1 if quality_moved else 0


if __name__ == "__main__":
    sys.exit(main())
