#!/usr/bin/env python3
"""STEP 5 - COST PER SUCCESSFUL TASK, INCLUDING THE FAILURES.

    python3 report.py

The failures go on the top. That is the whole idea, and it is the only
number in this repo that can tell you a change made things worse while
spending less money.
"""
from __future__ import annotations

from collections import defaultdict

from agent.ledger import read_all
from agent.runner import SUCCESS_DEFINITION


def main() -> None:
    runs = read_all()
    if not runs:
        print("No runs in the ledger yet. Run the agent first.")
        return

    total = sum(r["cost_usd"] for r in runs)
    ok = [r for r in runs if r["result"] == "success"]
    bad = [r for r in runs if r["result"] != "success"]
    wasted = sum(r["cost_usd"] for r in bad)

    print()
    print("  COST PER SUCCESSFUL TASK")
    print(f"  success means: {SUCCESS_DEFINITION}")
    print("  " + "-" * 62)
    print(f"  runs started            {len(runs)}")
    print(f"  succeeded               {len(ok)}      <- the denominator")
    print(f"  did not                 {len(bad)}      <- still counts on top")
    print(f"  total spend             ${total:.4f}")
    print("  " + "-" * 62)
    per_request = total / len(runs)
    print(f"  cost per request        ${per_request:.4f}   (pays by the mile)")
    if ok:
        per_success = total / len(ok)
        print(f"  cost per SUCCESSFUL     ${per_success:.4f}   (pays for arrival)")
        gap = (per_success / per_request - 1) * 100
        print(f"  the gap                 {gap:.0f}% higher, and it is the true number")
    else:
        print("  cost per SUCCESSFUL     undefined; nothing succeeded, and that is the finding")
    print(f"  failed-run tax          ${wasted:.4f}  ({wasted / total * 100 if total else 0:.0f}% of spend)")

    saved = sum(r.get("saved_by_checkpoint_usd", 0) for r in runs)
    if saved:
        print(f"  saved by checkpoints    ${saved:.4f}  (work not paid for twice)")

    by_reason: dict[str, list] = defaultdict(list)
    for r in bad:
        by_reason[r["result"]].append(r["cost_usd"])
    if by_reason:
        print("  " + "-" * 62)
        print("  where the wasted money went")
        for k, v in sorted(by_reason.items(), key=lambda kv: -sum(kv[1])):
            print(f"    {k:<10} {len(v):>3} run(s)   ${sum(v):.4f}")
    print()


if __name__ == "__main__":
    main()
