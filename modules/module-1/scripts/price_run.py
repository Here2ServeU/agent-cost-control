#!/usr/bin/env python3
"""MODULE 1 - CHECK YOUR ARITHMETIC, THEN EXTRAPOLATE YOUR OWN $4,200.

Do the sum by hand first. This script is for checking it afterwards,
and for the extrapolation at the end of the module.

    # a healthy run: steps, tokens, cost
    python3 run_agent.py --input samples/normal.json --verbose | python3 price_run.py

    # two minutes of the runaway, projected over a night nobody noticed
    timeout 120 python3 run_agent.py --input samples/malformed.json --verbose \\
        | python3 price_run.py --seconds 120 --hours 9.5

Rates are US dollars per million tokens. The defaults are the course's
"sonnet" rates; use the numbers from your provider's pricing page for
your own agent.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

USAGE = re.compile(r"usage:\s*(\{.*\})")


def main() -> int:
    ap = argparse.ArgumentParser(description="Price a run from its --verbose output.")
    ap.add_argument("file", nargs="?", help="saved --verbose output (default: stdin)")
    ap.add_argument("--input-rate", type=float, default=3.00, help="$ per million input tokens")
    ap.add_argument("--output-rate", type=float, default=15.00, help="$ per million output tokens")
    ap.add_argument("--seconds", type=float, help="how long the run was allowed to go")
    ap.add_argument("--hours", type=float, default=9.5, help="hours until somebody notices")
    a = ap.parse_args()

    text = open(a.file).read() if a.file else sys.stdin.read()
    blocks = [json.loads(m.group(1)) for m in USAGE.finditer(text)]
    if not blocks:
        print("No usage blocks found. Did you run the agent with --verbose?")
        return 1

    tin = sum(b["input_tokens"] for b in blocks)
    tout = sum(b["output_tokens"] for b in blocks)
    cin = tin * a.input_rate / 1_000_000
    cout = tout * a.output_rate / 1_000_000
    cost = cin + cout
    calls = len(blocks)

    print()
    print(f"  model calls (steps)     {calls}")
    print(f"  input tokens            {tin:>10,}   x ${a.input_rate:.2f}/M  = ${cin:.4f}")
    print(f"  output tokens           {tout:>10,}   x ${a.output_rate:.2f}/M = ${cout:.4f}")
    print(f"  cost of the run         ${cost:.4f}")
    print(f"  cost per call           ${cost / calls:.4f}")
    print(f"  token ratio in:out      {tin / tout:.1f} : 1")
    print(f"  cost ratio  in:out      {cin / cout:.1f} : 1   <- not the same thing")
    first, last = blocks[0]["input_tokens"], blocks[-1]["input_tokens"]
    print(f"  input tokens, call 1    {first:,}  ->  call {calls}: {last:,}   (the history is resent)")

    if a.seconds:
        per_hour = calls / a.seconds * 3600 * (cost / calls)
        overnight = per_hour * a.hours
        print()
        print(f"  calls in {a.seconds:.0f}s            {calls}")
        print(f"  x cost per call         ${cost / calls:.4f}")
        print(f"  = one hour              ${per_hour:,.2f}")
        print(f"  x {a.hours:g} hours to notice")
        print(f"  = YOUR NUMBER           ${overnight:,.2f}   <- one unnoticed loop")
        print()
        print("  Write it down. Every control in modules 2 to 6 is measured against it.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
