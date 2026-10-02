#!/usr/bin/env python3
"""MODULE 3: BUDGET CAPS AND KILL SWITCHES.

The module 2 agent, with caps and a switch added inside the envelope.
The agent's own logic is still untouched.

  1  the per-run cap        a running total, checked before each call
  2  decide what happens    catch BudgetExceeded, do what ON_BREACH says
  3  the daily cap          a total that survives between runs
  4  cap the runaway        the malformed input stops by itself
  5  the kill switch        checked before starting any new run

    RUN_BUDGET_USD=0.02 python3 run_agent.py --input samples/normal.json
    DAILY_BUDGET_USD=0.10 python3 run_agent.py --input samples/normal.json
    RUN_BUDGET_USD=0.50 python3 run_agent.py --input samples/malformed.json --max-seconds 120
    AGENT_ENABLED=false python3 run_agent.py --input samples/normal.json
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
from budget import AgentDisabled, Budget, BudgetExceeded
from sim_model import SimulatedModel

AGENT = "invoice-reader"
TEAM = "finance-ops"
MODEL = "sonnet"

PRICES_USD_PER_MTOK = {
    "haiku":  {"input": 0.80, "output": 4.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "opus":   {"input": 15.00, "output": 75.00},
}


def cost_usd(model: str, usage: dict[str, int]) -> float:
    p = PRICES_USD_PER_MTOK[model]
    return (usage["input_tokens"] * p["input"] + usage["output_tokens"] * p["output"]) / 1_000_000


def envelope(client: SimulatedModel, step: int, run_id: str, budget: Budget) -> tuple[dict, float]:
    budget.before_call()                        # STAGE 1 and 3: raises BudgetExceeded
    response = client.call(step, MODEL)
    usage = response["usage"]
    usd = cost_usd(MODEL, usage)
    budget.charge(usd)                          # spent is spent; record it first
    ledger.append_call({
        "run_id": run_id, "agent": AGENT, "team": TEAM, "model": MODEL, "step": step,
        "input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"],
        "cost_usd": round(usd, 8),
    })
    return response, usd


def main() -> int:
    ap = argparse.ArgumentParser(description="The course agent, capped.")
    ap.add_argument("--input", required=True, help="a task file from samples/")
    ap.add_argument("--max-seconds", type=float, help="a backstop; the cap should fire first")
    ap.add_argument("--pace", type=float, default=float(os.environ.get("AGENT_PACE", 0.2)),
                    help="seconds per model call (default 0.2)")
    ap.add_argument("--quiet", action="store_true", help="only print the verdict")
    a = ap.parse_args()

    task = json.loads(Path(a.input).read_text())
    client = SimulatedModel(task)
    budget = Budget()
    run_id = uuid.uuid4().hex[:8]
    started, step, done = time.time(), 0, []
    result, reason = "unknown", "finished"      # module 5 turns "finished" into success or failure

    try:
        budget.before_run()                     # STAGE 3 and 5: refuse before any work
        while True:
            if a.max_seconds and time.time() - started >= a.max_seconds:
                result, reason = "timeout", f"--max-seconds {a.max_seconds:g} reached"
                break
            response, usd = envelope(client, step + 1, run_id, budget)
            step += 1
            action = response["action"]
            done.append(action)
            if not a.quiet:
                print(f"run={run_id}  step {step:>3} {action['type'] + ':' + action['target']:<16} "
                      f"${usd:.4f}  run ${budget.run_spend:.4f}  "
                      f"day ${budget.day_spend():.4f}", flush=True)
            if action["type"] == "final":
                break
            time.sleep(a.pace)
    except AgentDisabled as e:
        result, reason = "refused", str(e)
    except BudgetExceeded as e:
        # STAGE 2: the behaviour you chose, on purpose.
        reason = str(e)
        if step == 0:
            result = "refused"                  # refused before a single call: costs nothing
        elif budget.on_breach == "kill":
            result = "killed"
        elif budget.on_breach == "drain":
            result = "capped"
            partial = ledger.LEDGER_DIR / "partial" / f"{run_id}.json"
            partial.parent.mkdir(parents=True, exist_ok=True)
            partial.write_text(json.dumps({"task": task.get("id"), "completed": done}, indent=2))
            reason += f" Drained: {len(done)} finished step(s) saved to {partial}."
        else:
            result = "capped"
    except KeyboardInterrupt:
        result, reason = "interrupted", "Ctrl-C"

    ledger.append_run({"run_id": run_id, "agent": AGENT, "team": TEAM, "model": MODEL,
                       "task": task.get("id"), "result": result, "reason": reason,
                       "steps": step, "cost_usd": round(budget.run_spend, 8)})
    print(f"\n  run {run_id}   {result.upper()}")
    print(f"  why          {reason}")
    print(f"  steps        {step}")
    print(f"  cost         ${budget.run_spend:.4f}   (cap ${budget.per_run:.2f}, on breach: {budget.on_breach})")
    print(f"  today        ${budget.day_spend():.4f}   (cap ${budget.per_day:.2f})")
    print(f"  wall clock   {time.time() - started:.1f}s\n")
    if result == "killed":
        return 137
    return 0 if result == "unknown" else 1


if __name__ == "__main__":
    sys.exit(main())
