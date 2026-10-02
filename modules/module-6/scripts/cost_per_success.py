#!/usr/bin/env python3
"""MODULE 5: COST PER SUCCESSFUL TASK, INCLUDING THE FAILURES.

    python3 cost_per_success.py --since 7d
    python3 cost_per_success.py --since 7d --compare-previous

All spend over the window, divided by the runs that succeeded. The
failures go on the TOP: they cost money and produced nothing, so they
make every success more expensive. That is the whole idea, and it is
the only number that can tell you a change made things worse while
spending less money.

Prints all three numbers: spend, successes, and the result; not just
the answer, and the definition of success with them, every time.
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict

import ledger
from success import SUCCESS_DEFINITION


def window(start: float, end: float) -> list[dict]:
    # Runs refused before a single call never started; they cost nothing and count nowhere.
    return [r for r in ledger.read_runs()
            if start <= r["ts"] < end and r["result"] != "refused"]


def summarise(runs: list[dict]) -> dict:
    spend = sum(r["cost_usd"] for r in runs)
    ok = sum(1 for r in runs if r["result"] == "success")
    return {
        "runs": len(runs), "ok": ok, "spend": spend,
        "per_request": spend / len(runs) if runs else None,
        "per_success": spend / ok if ok else None,
        "wasted": sum(r["cost_usd"] for r in runs if r["result"] != "success"),
    }


def money(x: float | None) -> str:
    return "undefined" if x is None else f"${x:.4f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Cost per successful task, failures on top.")
    ap.add_argument("--since", default="7d", help="window, e.g. 7d, 24h, 30m (default 7d)")
    ap.add_argument("--compare-previous", action="store_true",
                    help="also show the window before this one, and the change")
    a = ap.parse_args()

    span, now = ledger.parse_window(a.since), time.time()
    runs = window(now - span, now + 1)
    if not runs:
        print(f"No runs recorded in the last {a.since}. Run the agent first.")
        return 1
    cur = summarise(runs)

    print()
    print(f"  COST PER SUCCESSFUL TASK, last {a.since}")
    print(f"  success means: {SUCCESS_DEFINITION}")
    print("  " + "-" * 62)
    print(f"  runs started            {cur['runs']}")
    print(f"  succeeded               {cur['ok']}      <- the denominator")
    print(f"  did not                 {cur['runs'] - cur['ok']}      <- still counted on top")
    print(f"  total spend             ${cur['spend']:.4f}")
    print("  " + "-" * 62)
    print(f"  cost per request        {money(cur['per_request'])}   (pays by the mile)")
    if cur["per_success"] is None:
        print("  cost per SUCCESSFUL     undefined; nothing succeeded, and that is the finding")
    else:
        print(f"  cost per SUCCESSFUL     {money(cur['per_success'])}   (pays for arrival)")
        gap = (cur["per_success"] / cur["per_request"] - 1) * 100
        print(f"  the gap                 {gap:.0f}% higher, and it is the true number")
    print(f"  failed-run tax          ${cur['wasted']:.4f}  "
          f"({cur['wasted'] / cur['spend'] * 100 if cur['spend'] else 0:.0f}% of spend)")

    by: dict[str, list[float]] = defaultdict(list)
    for r in runs:
        if r["result"] != "success":
            by[r.get("stopped_by", r["result"])].append(r["cost_usd"])
    if by:
        print("  " + "-" * 62)
        print("  where the failed money went")
        for k, v in sorted(by.items(), key=lambda kv: -sum(kv[1])):
            label = "finished, failed the check" if k == "final" else k
            print(f"    {label:<28} {len(v):>3} run(s)   ${sum(v):.4f}")

    if a.compare_previous:
        prev = summarise(window(now - 2 * span, now - span))
        print("  " + "-" * 62)
        print(f"  previous {a.since}")
        if not prev["runs"]:
            print("    no runs in the previous window; nothing to compare yet")
        else:
            print(f"    runs {prev['runs']}, succeeded {prev['ok']}, spend ${prev['spend']:.4f}")
            print(f"    cost per SUCCESSFUL     {money(prev['per_success'])}")
            if prev["per_success"] and cur["per_success"]:
                move = (cur["per_success"] / prev["per_success"] - 1) * 100
                flag = "  <- go and look" if abs(move) >= 15 else ""
                print(f"    change                  {move:+.0f}%{flag}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
