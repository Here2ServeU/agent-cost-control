#!/usr/bin/env python3
"""The safe agent. Same agent as naive_agent.py, six steps later.

  python3 run_agent.py --input samples/malformed.json
  python3 run_agent.py --input samples/malformed.json --no-loop-detect
  python3 run_agent.py --input samples/malformed.json --no-caps --no-loop-detect
  python3 run_agent.py --input samples/good.json --resume
"""
from __future__ import annotations

import argparse
import sys

from agent.runner import Config, SafeAgent

VERDICT = {
    "success": "\033[92mSUCCESS\033[0m",
    "looped": "\033[93mSTOPPED: loop detected\033[0m",
    "capped": "\033[93mSTOPPED: budget cap\033[0m",
    "ceiling": "\033[93mSTOPPED: step ceiling\033[0m",
    "failed": "\033[91mFAILED\033[0m",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--resume", action="store_true", help="pick up from the last checkpoint")
    ap.add_argument("--no-caps", action="store_true", help="step 2 off; for proving the alert")
    ap.add_argument("--no-loop-detect", action="store_true", help="step 3 off; for proving the cap")
    ap.add_argument("--no-checkpoint", action="store_true", help="step 4 off; for measuring what it saves")
    ap.add_argument("--per-run-usd", type=float)
    ap.add_argument("--step-ceiling", type=int)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--push", action="store_true", help="push metrics to the pushgateway")
    a = ap.parse_args()

    cfg = Config.load(a.config)
    if a.no_caps:
        cfg.caps_enabled = False
    if a.no_loop_detect:
        cfg.loop_detection = False
    if a.no_checkpoint:
        cfg.checkpoints = False
    if a.per_run_usd is not None:
        cfg.per_run_usd = a.per_run_usd
    if a.step_ceiling is not None:
        cfg.step_ceiling = a.step_ceiling

    agent = SafeAgent(cfg, verbose=not a.quiet)
    r = agent.run(a.input, resume=a.resume)

    print()
    print(f"  run {r.run_id}   {VERDICT.get(r.result, r.result)}")
    print(f"  why          {r.reason}")
    print(f"  steps        {r.steps}")
    print(f"  cost         ${r.cost_usd:.4f}")
    if r.saved_by_checkpoint_usd:
        print(f"  not re-paid  ${r.saved_by_checkpoint_usd:.4f}  (work the checkpoint kept)")
    print(f"  wall clock   {r.duration_s}s")
    if a.push:
        print(f"  metrics      {agent.metrics.push()}")
    print()
    return 0 if r.result == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
