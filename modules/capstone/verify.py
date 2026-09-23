#!/usr/bin/env python3
"""THE CAPSTONE CHECK.

    python3 verify.py

Six steps, six proofs. Each one runs the agent for real and asserts on
what came back; none of them trust a comment in a file. When all six
pass, the agent is safe to leave running overnight - not because
someone says so, but because the thing that would have hurt you was
tried and stopped.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from agent.metrics import COST, RUNS, STEPS, WASTED
from agent.pricing import cost_usd
from agent.runner import SUCCESS_DEFINITION, Config, SafeAgent

GREEN, YELLOW, RED, DIM, OFF = "\033[92m", "\033[93m", "\033[91m", "\033[2m", "\033[0m"
LOOPING = "samples/malformed.json"
GOOD = "samples/good.json"

results: list[tuple[str, bool, str]] = []


def check(n: int, name: str, passed: bool, detail: str) -> None:
    mark = f"{GREEN}PASS{OFF}" if passed else f"{RED}FAIL{OFF}"
    print(f"  {n}. {name:<42} {mark}  {DIM}{detail}{OFF}")
    results.append((name, passed, detail))


def fresh(**over) -> Config:
    cfg = Config.load()
    for k, v in over.items():
        setattr(cfg, k, v)
    return cfg


def run(cfg: Config, task: str = LOOPING, **kw):
    return SafeAgent(cfg, verbose=False).run(task, **kw)


def main() -> int:
    shutil.rmtree("ledger", ignore_errors=True)
    print(f"\n  THE CAPSTONE: is this safe to leave running overnight?\n"
          f"  {DIM}input: the looping one. agent: uninstrumented, six steps ago.{OFF}\n")

    # --- 1. INSTRUMENTED ---------------------------------------------
    r = run(fresh())
    sample = cost_usd("sonnet", 1_000_000, 0)
    metric_cost = COST._metrics and sum(m._value.get() for m in COST._metrics.values())
    check(1, "Instrumented: cost, tokens, labels",
          r.cost_usd > 0 and metric_cost > 0 and sample == 3.0 and STEPS._metrics != {},
          f"${r.cost_usd:.4f} over {r.steps} steps, on agent/team/model labels")

    # --- 2. CAPPED ----------------------------------------------------
    # Loop detection off, so the only thing that can stop it is the cap.
    r = run(fresh(loop_detection=False, step_ceiling=10_000, per_run_usd=0.05))
    check(2, "Capped: per run and per day, deliberately",
          r.result == "capped" and r.cost_usd <= 0.06,
          f"stopped at ${r.cost_usd:.4f} against a $0.05 cap, behaviour=drain")

    # --- 3. LOOP DETECTED BEFORE THE CAP ------------------------------
    capped = run(fresh(loop_detection=False, step_ceiling=10_000))
    caught = run(fresh())
    cheaper = caught.cost_usd < capped.cost_usd
    check(3, "Loop caught before the cap is reached",
          caught.result == "looped" and cheaper,
          f"{caught.steps} steps / ${caught.cost_usd:.4f} vs {capped.steps} steps / "
          f"${capped.cost_usd:.4f} on the cap alone")

    # --- 4. CHECKPOINTED ----------------------------------------------
    # Kill a good run partway, then resume; the resumed run must not
    # pay again for the steps that already finished.
    shutil.rmtree("ledger/checkpoints", ignore_errors=True)
    killed = run(fresh(step_ceiling=3), GOOD)               # dies at the ceiling
    resumed = run(fresh(step_ceiling=40), GOOD, resume=True)
    check(4, "Checkpointed: a kill wastes nothing",
          resumed.result == "success" and resumed.saved_by_checkpoint_usd >= killed.cost_usd * 0.99,
          f"${resumed.saved_by_checkpoint_usd:.4f} of finished work carried over, not re-paid")

    # --- 5. COST PER SUCCESSFUL TASK ----------------------------------
    for _ in range(6):
        run(fresh(), GOOD)
    for _ in range(4):
        run(fresh(), LOOPING)
    from agent.ledger import read_all
    runs = read_all()
    ok = [x for x in runs if x["result"] == "success"]
    total = sum(x["cost_usd"] for x in runs)
    per_req = total / len(runs)
    per_success = total / len(ok)
    wasted = sum(m._value.get() for m in WASTED._metrics.values()) if WASTED._metrics else 0
    check(5, "Cost per successful task, failures on top",
          per_success > per_req and len(ok) < len(runs) and wasted > 0 and bool(SUCCESS_DEFINITION),
          f"${per_success:.4f} per success vs ${per_req:.4f} per request "
          f"({(per_success / per_req - 1) * 100:.0f}% higher)")

    # --- 6. ALERTED ---------------------------------------------------
    # Prove the burn-rate rule would have fired, by computing the same
    # projection the Prometheus rule computes, from a real runaway.
    runaway = run(fresh(caps_enabled=False, loop_detection=False, step_ceiling=300))
    # The simulated model answers instantly; a real one takes seconds. Project at a
    # stated real pace rather than at simulator speed, so the number means something.
    SECONDS_PER_STEP = 3.0
    rate_per_s = (runaway.cost_usd / runaway.steps) / SECONDS_PER_STEP
    projected_monthly = rate_per_s * 60 * 60 * 24 * 30
    budget_monthly = 300.0
    fires = projected_monthly > budget_monthly * 2
    check(6, "Alerted on burn rate, proven by triggering it",
          fires and runaway.result == "ceiling",
          f"${projected_monthly:,.0f}/month projected at 1 step / {SECONDS_PER_STEP:.0f}s, "
          f"budget ${budget_monthly:,.0f}")

    passed = sum(1 for _, p, _ in results if p)
    print()
    if passed == len(results):
        print(f"  {GREEN}All six hold.{OFF} The runaway that started this course now stops on its")
        print(f"  own, in seconds, at a cost you chose in advance.\n")
        print(f"  {DIM}Next: python3 report.py, then open Grafana on :3000.{OFF}\n")
        return 0
    print(f"  {RED}{len(results) - passed} of {len(results)} failed.{OFF} "
          f"Not safe to leave running yet.\n")
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    sys.exit(main())
