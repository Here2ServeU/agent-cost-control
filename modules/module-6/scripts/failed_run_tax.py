#!/usr/bin/env python3
"""MODULE 4: YOUR FAILED-RUN TAX.

    python3 failed_run_tax.py --since 30d

Reads the recorded runs, sums all spend, sums spend on runs that
succeeded, and prints the difference as a share of the total. That
percentage is your number. In module 6 it goes on a dashboard, and it
becomes the thing you watch to know whether any of this still works.
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict

import ledger


def main() -> int:
    ap = argparse.ArgumentParser(description="Share of spend that went to runs that did not succeed.")
    ap.add_argument("--since", default="30d", help="window, e.g. 30d, 7d, 12h, 15m (default 30d)")
    a = ap.parse_args()

    cutoff = time.time() - ledger.parse_window(a.since)
    runs = [r for r in ledger.read_runs() if r["ts"] >= cutoff]
    if not runs:
        print(f"No runs recorded in the last {a.since}. Run the agent first.")
        return 1

    total = sum(r["cost_usd"] for r in runs)
    good = sum(r["cost_usd"] for r in runs if r["result"] == "success")
    wasted = total - good
    ok = sum(1 for r in runs if r["result"] == "success")

    print()
    print(f"  FAILED-RUN TAX, last {a.since}")
    print("  " + "-" * 52)
    print(f"  runs                    {len(runs)}   ({ok} succeeded)")
    print(f"  total spend             ${total:.4f}")
    print(f"  spend on successes      ${good:.4f}")
    print(f"  spend on the rest       ${wasted:.4f}")
    print(f"  FAILED-RUN TAX          {wasted / total * 100 if total else 0:.0f}% of spend")

    by: dict[str, list[float]] = defaultdict(list)
    for r in runs:
        if r["result"] != "success":
            by[r["result"]].append(r["cost_usd"])
    if by:
        print("  " + "-" * 52)
        print("  where it went")
        for k, v in sorted(by.items(), key=lambda kv: -sum(kv[1])):
            print(f"    {k:<12} {len(v):>3} run(s)   ${sum(v):.4f}")
    carried = sum(r.get("carried_usd", 0) for r in runs)
    if carried:
        print(f"  saved by checkpoints    ${carried:.4f}  (work not paid for twice)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
