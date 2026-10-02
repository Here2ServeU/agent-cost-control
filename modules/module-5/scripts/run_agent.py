#!/usr/bin/env python3
"""MODULE 5: COST PER SUCCESSFUL TASK.

The module 4 agent (caps, switch, step limit, loop detection,
checkpoints), with one change: "it reached a final answer" is replaced
by the definition written down in SUCCESS.md, checked by success.py.
The result label now says success or failure; never unknown; and the
failures still count on the top of the division.

    cat SUCCESS.md
    python3 metrics_server.py &
    python3 run_agent.py --input samples/normal.json && curl -s localhost:8000/metrics | grep result=
    python3 run_agent.py --input samples/incomplete.json     # finishes cleanly; still a failure
    python3 cost_per_success.py --since 7d
    python3 cost_per_success.py --since 7d --compare-previous
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
from checkpoint import Checkpoint
from loops import LoopDetected, LoopDetector, StepLimitReached, check_ceiling, max_steps
from sim_model import ModelError, SimulatedModel
from success import SUCCESS_DEFINITION, is_success

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


class Interrupted(Exception):
    pass


def main() -> int:
    ap = argparse.ArgumentParser(description="The course agent: capped, bounded, checkpointed.")
    ap.add_argument("--input", required=True, help="a task file from samples/")
    ap.add_argument("--run-id", help="a fixed name, so a second run finds the first run's checkpoint")
    ap.add_argument("--retries", type=int, default=1, help="attempts before giving up (default 1)")
    ap.add_argument("--no-loop-detect", action="store_true", help="detector off; to see the ceiling work alone")
    ap.add_argument("--stop-after", type=int, help="interrupt after this many calls (a scripted Ctrl-C)")
    ap.add_argument("--max-seconds", type=float, help="a backstop; the limits should fire first")
    ap.add_argument("--pace", type=float, default=float(os.environ.get("AGENT_PACE", 0.2)),
                    help="seconds per model call (default 0.2)")
    ap.add_argument("--quiet", action="store_true", help="only print the verdict")
    a = ap.parse_args()

    task = json.loads(Path(a.input).read_text())
    run_id = a.run_id or uuid.uuid4().hex[:8]
    budget, ckpt, ceiling = Budget(), Checkpoint(run_id), max_steps()
    started = time.time()

    # STAGE 3: pick up where the last run with this id left off.
    completed, carried = ckpt.load()
    if completed:
        print(f"resuming {run_id}: {len(completed)} step(s) already done, "
              f"${carried:.4f} already spent and not paid twice")
    budget.run_spend = carried
    spent, calls, attempt = 0.0, 0, 0
    result, reason = "failed", "ran out of attempts"

    def charge(step: int, usage: dict[str, int]) -> float:
        nonlocal spent, calls
        usd = cost_usd(MODEL, usage)
        budget.charge(usd)
        spent += usd
        calls += 1
        ledger.append_call({
            "run_id": run_id, "agent": AGENT, "team": TEAM, "model": MODEL, "step": step,
            "input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"],
            "cost_usd": round(usd, 8),
        })
        return usd

    try:
        budget.before_run()
        for attempt in range(1, max(a.retries, 1) + 1):
            client = SimulatedModel(task, attempt)
            detector = LoopDetector(enabled=not a.no_loop_detect)
            if not ckpt.on:
                completed = []                  # no checkpoint: every retry starts from zero
            try:
                while True:
                    step = len(completed) + 1
                    check_ceiling(len(completed), ceiling)          # STAGE 1
                    budget.before_call()
                    if a.max_seconds and time.time() - started >= a.max_seconds:
                        raise Interrupted(f"--max-seconds {a.max_seconds:g} reached")
                    try:
                        response = client.call(step, MODEL)
                    except ModelError as e:
                        charge(step, e.usage)                       # a failed call is still billed
                        raise
                    usd = charge(step, response["usage"])
                    action = response["action"]
                    detector.check(action)                          # STAGE 2
                    completed.append({"step": step, "type": action["type"],
                                      "target": action["target"], "usd": round(usd, 8)})
                    ckpt.save(completed, carried + spent)           # STAGE 3: after every step
                    if not a.quiet:
                        print(f"run={run_id}  attempt {attempt}  step {step:>3} "
                              f"{action['type'] + ':' + action['target']:<16} ${usd:.4f}   "
                              f"run total ${carried + spent:.4f}", flush=True)
                    if action["type"] == "final":
                        # STAGE 2: the check from SUCCESS.md sets the result label.
                        if is_success(action.get("output")):
                            result, reason = "success", SUCCESS_DEFINITION
                        else:
                            result, reason = "failure", (f"finished, but the answer failed the check "
                                                         f"({SUCCESS_DEFINITION}): {action.get('output')}")
                        break
                    if a.stop_after and calls >= a.stop_after:
                        raise KeyboardInterrupt
                    time.sleep(a.pace)
                break
            except ModelError as e:
                print(f"run={run_id}  attempt {attempt} FAILED at step {step}: {e}"
                      + ("" if attempt == a.retries else "  -> retrying"), flush=True)
                result, reason = "failed", f"{e}; gave up after {attempt} attempt(s)"
    except StepLimitReached as e:
        result, reason = "ceiling", str(e)
    except LoopDetected as e:
        result, reason = "looped", str(e)
    except BudgetExceeded as e:
        result, reason = ("refused" if calls == 0 else "capped"), str(e)
    except AgentDisabled as e:
        result, reason = "refused", str(e)
    except (KeyboardInterrupt, Interrupted) as e:
        result, reason = "interrupted", str(e) or "Ctrl-C"
        if ckpt.on:
            reason += f"; {len(completed)} finished step(s) are in {ckpt.path}"

    if result in ("success", "failure"):
        ckpt.clear()                    # it finished; there is nothing left to resume
    # Two values on the label, success or failure; the detail travels in stopped_by.
    stopped_by = {"success": "final", "failure": "final"}.get(result, result)
    label = result if result in ("success", "refused") else "failure"
    ledger.append_run({"run_id": run_id, "agent": AGENT, "team": TEAM, "model": MODEL,
                       "task": task.get("id"), "result": label, "stopped_by": stopped_by,
                       "reason": reason, "success_definition": SUCCESS_DEFINITION,
                       "steps": calls, "attempts": attempt, "cost_usd": round(spent, 8),
                       "carried_usd": round(carried, 8), "checkpoints": ckpt.on})
    print(f"\n  run {run_id}   {label.upper()}" + ("" if label == result else f"  ({result})"))
    print(f"  why          {reason}")
    print(f"  model calls  {calls}   (attempts: {attempt}, checkpoints: {'on' if ckpt.on else 'off'})")
    print(f"  cost         ${spent:.4f}   this time")
    if carried:
        print(f"  not re-paid  ${carried:.4f}   (finished work the checkpoint kept)")
    print(f"  wall clock   {time.time() - started:.1f}s\n")
    return 0 if label == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
