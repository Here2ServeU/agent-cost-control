#!/usr/bin/env python3
"""MODULE 2 - MAKING COST VISIBLE.

The same agent as module 1, with one thing added: an envelope around the
model call that keeps the receipt. The agent's own logic is untouched,
and nothing is stopped yet - you cannot sensibly choose a limit until
you can see what normal looks like.

The four stages of the build, all in this file:

  1  catch the receipt      read the usage block instead of dropping it
  2  turn tokens into money two rates, multiply, add
  3  add the four labels    agent, team, run, result
  4  make the counter       every call is written to the ledger, and
                            metrics_server.py serves it on :8000

    python3 run_agent.py --input samples/normal.json
    python3 metrics_server.py &
    python3 run_agent.py --input samples/normal.json && curl -s localhost:8000/metrics | grep agent_cost
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

import ledger
from sim_model import SimulatedModel

# STAGE 3: who is spending. Chosen once, attached to everything.
AGENT = "invoice-reader"
TEAM = "finance-ops"
MODEL = "sonnet"

# STAGE 2: US dollars per million tokens, from the provider's pricing page.
# Input and output are priced differently; never average them into one.
PRICES_USD_PER_MTOK = {
    "haiku":  {"input": 0.80, "output": 4.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "opus":   {"input": 15.00, "output": 75.00},
}


def cost_usd(model: str, usage: dict[str, int]) -> float:
    p = PRICES_USD_PER_MTOK[model]
    return (usage["input_tokens"] * p["input"] + usage["output_tokens"] * p["output"]) / 1_000_000


def envelope(client: SimulatedModel, step: int, run_id: str) -> tuple[dict, float]:
    """STAGE 1: wrap the call; do not rewrite it.

    The model is called exactly as before. The envelope only reads the
    usage block, prices it, and writes the receipt down.
    """
    response = client.call(step, MODEL)
    usage = response["usage"]
    usd = cost_usd(MODEL, usage)
    ledger.append_call({
        "run_id": run_id, "agent": AGENT, "team": TEAM, "model": MODEL, "step": step,
        "input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"],
        "cost_usd": round(usd, 8),
    })
    return response, usd


def main() -> int:
    ap = argparse.ArgumentParser(description="The course agent, instrumented.")
    ap.add_argument("--input", required=True, help="a task file from samples/")
    ap.add_argument("--verbose", action="store_true", help="also print the raw usage block")
    ap.add_argument("--max-seconds", type=float, help="stop after this long (nothing else will stop it yet)")
    ap.add_argument("--pace", type=float, default=float(os.environ.get("AGENT_PACE", 0.2)),
                    help="seconds per model call (default 0.2)")
    a = ap.parse_args()

    task = json.loads(Path(a.input).read_text())
    client = SimulatedModel(task)
    run_id = uuid.uuid4().hex[:8]       # once, at the start of the run - not inside the envelope
    result = "unknown"                  # module 5 sets this properly
    started, spent, step = time.time(), 0.0, 0

    try:
        while True:
            if a.max_seconds and time.time() - started >= a.max_seconds:
                print(f"stopped by --max-seconds after {step} calls", file=sys.stderr)
                break
            step += 1
            response, usd = envelope(client, step, run_id)
            spent += usd
            action, usage = response["action"], response["usage"]
            print(f"agent={AGENT} team={TEAM} run={run_id} result={result}  "
                  f"step {step:>3} {action['type'] + ':' + action['target']:<16} "
                  f"in={usage['input_tokens']:>5} out={usage['output_tokens']:>4}  "
                  f"${usd:.4f}  run total ${spent:.4f}", flush=True)
            if a.verbose:
                print(f"           usage: {json.dumps(usage)}", flush=True)
            if action["type"] == "final":
                break
            time.sleep(a.pace)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)

    ledger.append_run({"run_id": run_id, "agent": AGENT, "team": TEAM, "model": MODEL,
                       "task": task.get("id"), "result": result, "steps": step,
                       "cost_usd": round(spent, 8)})
    print(f"\n  run {run_id}: {step} calls, ${spent:.4f}   (receipts in ledger/)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
