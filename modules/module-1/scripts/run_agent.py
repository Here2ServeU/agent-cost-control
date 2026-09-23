#!/usr/bin/env python3
"""MODULE 1 - THE AGENT YOU START WITH.

It has no cost accounting, no cap, no loop detection, no checkpoints and
no definition of success. It is the state most agents are actually in.

    python3 run_agent.py --input samples/normal.json --verbose
    python3 run_agent.py --input samples/normal.json --verbose | grep -c 'usage'
    timeout 120 python3 run_agent.py --input samples/malformed.json --verbose

--verbose prints the raw usage block from every model call. The agent
itself never reads it; it is thrown away, exactly as it is in most code.
Your job in this module is to price a run by hand from those numbers.

The malformed input never finishes. Always run it with a time limit:
`timeout 120` on macOS/Linux, or `--max-seconds 120` anywhere.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from sim_model import SimulatedModel


def main() -> int:
    ap = argparse.ArgumentParser(description="The uninstrumented course agent.")
    ap.add_argument("--input", required=True, help="a task file from samples/")
    ap.add_argument("--verbose", action="store_true", help="print the raw usage block of every call")
    ap.add_argument("--max-seconds", type=float, help="stop after this long (the timeout for Windows)")
    ap.add_argument("--pace", type=float, default=float(os.environ.get("AGENT_PACE", 0.2)),
                    help="seconds per model call; a real model takes seconds (default 0.2)")
    a = ap.parse_args()

    task = json.loads(Path(a.input).read_text())
    model = SimulatedModel(task)
    started = time.time()

    step = 0
    try:
        while True:                     # no ceiling. none. this is the bug.
            if a.max_seconds and time.time() - started >= a.max_seconds:
                print(f"stopped by --max-seconds after {step} calls", file=sys.stderr)
                return 124
            step += 1
            response = model.call(step)
            action = response["action"]
            print(f"step {step:>4}  {action['type']}:{action['target']}", flush=True)
            if a.verbose:
                print(f"           usage: {json.dumps(response['usage'])}", flush=True)
            if action["type"] == "final":
                print("done")
                return 0
            time.sleep(a.pace)
    except KeyboardInterrupt:
        print(f"\ninterrupted after {step} calls", file=sys.stderr)
        return 130
    except BrokenPipeError:             # e.g. piped into `head`
        return 0


if __name__ == "__main__":
    sys.exit(main())
