#!/usr/bin/env python3
"""MODULE 6 - OPERATING IT.

The finished agent: everything from modules 2 to 5, plus model routing.

  instrumented     every call priced and written to the ledger (module 2)
  capped           per run and per day, and a kill switch      (module 3)
  bounded          step limit and loop detection               (module 4)
  checkpointed     a kill wastes nothing                       (module 4)
  labelled         success or failure, from SUCCESS.md         (module 5)
  routed           one step type to a cheaper model            (module 6)

    python3 run_agent.py --input samples/malformed.json                     # the capstone
    python3 run_agent.py --input samples/normal.json --repeat 20 --batch baseline --quiet
    python3 run_agent.py --input samples/normal.json --repeat 20 --batch routed --route read --quiet
    python3 compare_runs.py --before baseline --after routed

Proving the alert fires means turning the caps off, deliberately:

    MAX_STEPS=600 python3 run_agent.py --input samples/malformed.json \\
        --no-caps --no-loop-detect --pace 0.5 --quiet &

Stop it once the alert fires, and never leave it running unattended.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import ledger
from budget import AgentDisabled, Budget, BudgetExceeded
from checkpoint import Checkpoint
from loops import LoopDetected, LoopDetector, StepLimitReached, check_ceiling, max_steps
from sim_model import PLAN, ModelError, SimulatedModel
from success import SUCCESS_DEFINITION, is_success

AGENT = "invoice-reader"
TEAM = os.environ.get("AGENT_TEAM", "finance-ops")
MODEL = "sonnet"            # the default, for every step not routed
CHEAP_MODEL = "haiku"       # where routed steps go

PRICES_USD_PER_MTOK = {
    "haiku":  {"input": 0.80, "output": 4.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "opus":   {"input": 15.00, "output": 75.00},
}


def cost_usd(model: str, usage: dict[str, int]) -> float:
    p = PRICES_USD_PER_MTOK[model]
    return (usage["input_tokens"] * p["input"] + usage["output_tokens"] * p["output"]) / 1_000_000


def planned_step_type(step: int) -> str:
    """The agent's own plan says what kind of step comes next; route on that."""
    return PLAN[step - 1][0] if step <= len(PLAN) else "final"


def expected_amount(task: dict[str, Any]) -> float | None:
    try:
        return float(str(task.get("amount")).replace(",", ""))
    except (TypeError, ValueError):
        return None


class Interrupted(Exception):
    pass


def run_once(task: dict[str, Any], a: argparse.Namespace, run_id: str) -> dict[str, Any]:
    budget, ckpt, ceiling = Budget(), Checkpoint(run_id), max_steps()
    if a.no_caps:
        budget.per_run = budget.per_day = float("inf")
    routed = set(a.route or [])
    started = time.time()

    completed, carried = ckpt.load()
    if completed:
        print(f"resuming {run_id}: {len(completed)} step(s) already done, "
              f"${carried:.4f} already spent and not paid twice")
    budget.run_spend = carried
    spent, calls, attempt = 0.0, 0, 0
    result, reason, output = "failed", "ran out of attempts", None

    def charge(step: int, model: str, usage: dict[str, int]) -> float:
        nonlocal spent, calls
        usd = cost_usd(model, usage)
        budget.charge(usd)
        spent += usd
        calls += 1
        ledger.append_call({
            "run_id": run_id, "agent": AGENT, "team": TEAM, "model": model, "step": step,
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
                completed = []
            try:
                while True:
                    step = len(completed) + 1
                    check_ceiling(len(completed), ceiling)
                    budget.before_call()
                    if a.max_seconds and time.time() - started >= a.max_seconds:
                        raise Interrupted(f"--max-seconds {a.max_seconds:g} reached")
                    model = CHEAP_MODEL if planned_step_type(step) in routed else MODEL
                    try:
                        response = client.call(step, model)
                    except ModelError as e:
                        charge(step, model, e.usage)
                        raise
                    usd = charge(step, model, response["usage"])
                    action = response["action"]
                    detector.check(action)
                    completed.append({"step": step, "type": action["type"], "model": model,
                                      "target": action["target"], "usd": round(usd, 8)})
                    ckpt.save(completed, carried + spent)
                    if not a.quiet:
                        print(f"run={run_id}  step {step:>3} {action['type'] + ':' + action['target']:<16} "
                              f"{model:<7} ${usd:.4f}   run total ${carried + spent:.4f}", flush=True)
                    if action["type"] == "final":
                        output = action.get("output")
                        if is_success(output):
                            result, reason = "success", SUCCESS_DEFINITION
                        else:
                            result, reason = "failure", f"finished, but the answer failed the check: {output}"
                        break
                    if a.stop_after and calls >= a.stop_after:
                        raise KeyboardInterrupt
                    time.sleep(a.pace)
                break
            except ModelError as e:
                if not a.quiet:
                    print(f"run={run_id}  attempt {attempt} FAILED at step {step}: {e}", flush=True)
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

    if result in ("success", "failure"):
        ckpt.clear()
    label = result if result in ("success", "refused") else "failure"
    exp = expected_amount(task)
    record = {
        "run_id": run_id, "agent": AGENT, "team": TEAM, "model": MODEL,
        "task": task.get("id"), "batch": a.batch, "routed": sorted(routed),
        "result": label, "stopped_by": {"success": "final", "failure": "final"}.get(result, result),
        "reason": reason, "success_definition": SUCCESS_DEFINITION,
        # quality, separately from success: did it get the right answer?
        "correct": bool(output) and exp is not None and output.get("amount") == exp,
        "steps": calls, "attempts": attempt, "cost_usd": round(spent, 8),
        "carried_usd": round(carried, 8), "caps": not a.no_caps,
        "duration_s": round(time.time() - started, 3),
    }
    ledger.append_run(record)
    return record


def main() -> int:
    ap = argparse.ArgumentParser(description="The finished course agent.")
    ap.add_argument("--input", required=True, help="a task file from samples/")
    ap.add_argument("--run-id", help="a fixed name, so a second run finds the first run's checkpoint")
    ap.add_argument("--retries", type=int, default=1, help="attempts before giving up (default 1)")
    ap.add_argument("--route", action="append", metavar="STEP_TYPE",
                    help=f"send this step type to {CHEAP_MODEL}: read, parse, validate, lookup, write (repeatable)")
    ap.add_argument("--repeat", type=int, default=1, help="run this many tasks like this one (default 1)")
    ap.add_argument("--batch", default="default", help="a name for this batch, for compare_runs.py")
    ap.add_argument("--no-caps", action="store_true", help="module 3 caps OFF; only to prove the alert fires")
    ap.add_argument("--no-loop-detect", action="store_true", help="loop detection off")
    ap.add_argument("--stop-after", type=int, help="interrupt after this many calls (a scripted Ctrl-C)")
    ap.add_argument("--max-seconds", type=float, help="a backstop per run")
    ap.add_argument("--pace", type=float, default=float(os.environ.get("AGENT_PACE", 0.2)),
                    help="seconds per model call (default 0.2)")
    ap.add_argument("--quiet", action="store_true", help="one line per run")
    a = ap.parse_args()

    base = json.loads(Path(a.input).read_text())
    if a.no_caps:
        print("WARNING: budget caps are OFF. This is only for proving the alert fires. "
              "Stop this run when it has, and do not leave it unattended.", file=sys.stderr)

    records = []
    for i in range(max(a.repeat, 1)):
        task = dict(base)
        if a.repeat > 1:        # twenty different invoices of the same kind, not one twenty times
            task["seed"] = int(base.get("seed", 7)) + i
            task["id"] = f"{base.get('id', 'task')}-{i + 1:02d}"
        run_id = a.run_id if (a.run_id and a.repeat == 1) else uuid.uuid4().hex[:8]
        r = run_once(task, a, run_id)
        records.append(r)
        verdict = r["result"].upper() + ("" if r["stopped_by"] in ("final", "refused") else f" ({r['stopped_by']})")
        if a.quiet:
            print(f"  run {r['run_id']}  {r['task']:<18} {verdict:<22} {r['steps']:>3} calls  ${r['cost_usd']:.4f}")
        else:
            print(f"\n  run {r['run_id']}   {verdict}")
            print(f"  why          {r['reason']}")
            print(f"  model calls  {r['steps']}   (attempts: {r['attempts']})")
            print(f"  cost         ${r['cost_usd']:.4f}")
            if r["carried_usd"]:
                print(f"  not re-paid  ${r['carried_usd']:.4f}   (finished work the checkpoint kept)")
            print(f"  wall clock   {r['duration_s']}s\n")

    if len(records) > 1:
        total = sum(r["cost_usd"] for r in records)
        ok = sum(1 for r in records if r["result"] == "success")
        print(f"\n  batch '{a.batch}': {len(records)} runs, {ok} succeeded, ${total:.4f} total\n")
    return 0 if all(r["result"] == "success" for r in records) else 1


if __name__ == "__main__":
    sys.exit(main())
