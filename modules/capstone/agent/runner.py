"""The safe agent: all six steps, in one loop you can read in a minute.

Read the run() method top to bottom. Every safety mechanism in this
course appears exactly once, in the order it has to fire.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import ledger
from .budget import Budget, BudgetExceeded
from .checkpoint import Checkpoint
from .llm import SimulatedModel
from .loops import LoopDetector
from .metrics import Metrics
from .pricing import cost_usd

# STEP 5 - the definition of success, written down, in code, once.
# "It passed a check": the run finished AND produced the field the task
# asked for. Not "it did not crash" (too generous) and not "a human
# accepted it" (true, but you cannot run it a hundred times a day).
SUCCESS_DEFINITION = "produced the required output field and passed validation"


@dataclass
class Config:
    agent: str = "invoice-reader"
    team: str = "finance-ops"
    model: str = "sonnet"
    step_ceiling: int = 40
    per_run_usd: float = 0.15
    per_day_usd: float = 10.00
    on_breach: str = "drain"
    caps_enabled: bool = True
    loop_detection: bool = True
    checkpoints: bool = True

    @classmethod
    def load(cls, path: str | Path = "config.json") -> "Config":
        p = Path(path)
        return cls(**json.loads(p.read_text())) if p.exists() else cls()


@dataclass
class Result:
    run_id: str
    result: str                       # success | failed | capped | looped | ceiling
    reason: str
    steps: int
    cost_usd: float
    saved_by_checkpoint_usd: float
    duration_s: float
    extras: dict[str, Any] = field(default_factory=dict)


class SafeAgent:
    def __init__(self, cfg: Config, verbose: bool = True) -> None:
        self.cfg, self.verbose = cfg, verbose
        self.metrics = Metrics(cfg.agent, cfg.team, cfg.model)

    def log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def run(self, task_path: str, resume: bool = False) -> Result:
        task = json.loads(Path(task_path).read_text())
        task_id = task.get("id", Path(task_path).stem)
        run_id = uuid.uuid4().hex[:8]          # in the ledger, never a metric label
        t0 = time.time()

        budget = Budget(self.cfg.per_run_usd, self.cfg.per_day_usd,
                        self.cfg.on_breach, enabled=self.cfg.caps_enabled)
        detector = LoopDetector(enabled=self.cfg.loop_detection)
        ckpt = Checkpoint(task_id, enabled=self.cfg.checkpoints)
        model = SimulatedModel(task, self.cfg.model)

        # STEP 4 in action: pick up where the kill left off.
        completed, already_spent = ckpt.load() if resume else ([], 0.0)
        if completed:
            self.log(f"resuming: {len(completed)} step(s) already done, "
                     f"${already_spent:.4f} already spent and not paid twice")
            model.n = len(completed)

        spent, result, reason = 0.0, "failed", "ran out of road"
        seen_targets = {c["target"] for c in completed}

        for _ in range(self.cfg.step_ceiling - len(completed)):
            # Pre-flight: do not start a step the budget cannot finish.
            if budget.would_exceed(0.01):
                result, reason = "capped", "pre-flight: next step would cross the per-run cap"
                break

            action, usage = model.next_action()
            usd = cost_usd(self.cfg.model, usage["input_tokens"], usage["output_tokens"])
            spent += usd

            # STEP 1: record it. Every step, no exceptions, before anything
            # can go wrong; you want the cost of the step that killed you.
            self.metrics.record_step(usage["input_tokens"], usage["output_tokens"], usd)

            made_progress = action["target"] not in seen_targets and action["type"] != "explore"
            seen_targets.add(action["target"])
            completed.append({"type": action["type"], "target": action["target"], "usd": usd})

            sig = f"{action['type']}:{action['target']}"
            self.log(f"  step {len(completed):>3}  {sig:<22} "
                     f"${usd:.4f}   run total ${spent + already_spent:.4f}")

            # STEP 4: save after every completed step.
            ckpt.save(completed, spent + already_spent)

            if action["type"] == "final":
                result, reason = "success", SUCCESS_DEFINITION
                break

            # STEP 3: cheap stop, before the expensive one.
            loop = detector.observe(action, made_progress)
            if loop:
                result, reason = "looped", loop
                break

            # STEP 2: the seatbelt.
            try:
                budget.charge(usd)
            except BudgetExceeded as e:
                result, reason = "capped", str(e)
                break
        else:
            result, reason = "ceiling", f"step ceiling of {self.cfg.step_ceiling} reached"

        total = round(spent + already_spent, 8)

        # STEP 5: label the outcome so it counts in the right place.
        self.metrics.record_run(result if result == "success" else "failure", total)

        if result == "success":
            ckpt.clear()               # nothing to resume; do not leave a stale one

        res = Result(run_id, result, reason, len(completed), total,
                     already_spent, round(time.time() - t0, 3))
        ledger.append({
            "run_id": run_id, "agent": self.cfg.agent, "team": self.cfg.team,
            "model": self.cfg.model, "task": task_id, "result": res.result,
            "reason": res.reason, "steps": res.steps, "cost_usd": res.cost_usd,
            "saved_by_checkpoint_usd": res.saved_by_checkpoint_usd,
            "duration_s": res.duration_s,
            "success_definition": SUCCESS_DEFINITION,
            "caps_enabled": self.cfg.caps_enabled,
            "loop_detection": self.cfg.loop_detection,
        })
        return res
