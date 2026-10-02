"""The model call, simulated.

This course is about controlling what an agent costs, not about spending
money to learn it. This file answers like a model would: an action to
take and a usage block saying how many tokens that took; all without
calling anything. Every script in this folder runs offline, for free,
and gives the same numbers every time.

Swap `SimulatedModel.call` for a real API call and the rest of the
scripts keep working: they only ever read `response["action"]` and
`response["usage"]`, which is the same shape every provider returns.

The sample inputs pick the behaviour:

  normal.json      converges in six steps          (the control)
  malformed.json   bounces: parse, validate, parse, validate, forever
  loop.json        stuck: the same call on the same field, forever
  drifting.json    never repeats, never finishes
  flaky.json       fails partway the first times you try it
  incomplete.json  finishes cleanly, with the answer missing

Two facts from module 1 are built in, because they are what make agent
cost behave the way it does:

  * input tokens GROW with every step (each call resends the history)
    until the context is trimmed, so long runs cost more than linearly;
  * input and output are counted separately, because they are priced
    separately.
"""
from __future__ import annotations

import random
from typing import Any

PLAN = [
    ("read", "input"),
    ("parse", "amount"),
    ("validate", "amount"),
    ("lookup", "vendor"),
    ("write", "record"),
]
HISTORY_TOKENS_PER_STEP = 420    # what each earlier step adds to the next prompt
HISTORY_KEPT_STEPS = 40          # after this, old history is trimmed


class ModelError(Exception):
    """A call that failed after the tokens were already spent."""

    def __init__(self, message: str, usage: dict[str, int]) -> None:
        super().__init__(message)
        self.usage = usage


class SimulatedModel:
    def __init__(self, task: dict[str, Any], attempt: int = 1) -> None:
        self.task = task
        self.shape = task.get("shape", "converging")
        self.seed = int(task.get("seed", 7))
        self.attempt = attempt
        self.misread = False     # set when a cheap model got the parse wrong

    def _usage(self, step: int, final: bool = False) -> dict[str, int]:
        # Seeded by step, so a resumed run sees exactly the same numbers.
        rng = random.Random(self.seed * 1000 + step)
        history = HISTORY_TOKENS_PER_STEP * min(step - 1, HISTORY_KEPT_STEPS)
        return {
            "input_tokens": 1400 + history + rng.randint(0, 150),
            "output_tokens": rng.randint(90, 160) if final else rng.randint(250, 450),
        }

    def call(self, step: int, model: str = "sonnet") -> dict[str, Any]:
        """One model call. Returns {"model", "action", "usage"}."""
        if self.shape == "flaky":
            fail_at = int(self.task.get("fail_at_step", 4))
            if step == fail_at and self.attempt <= int(self.task.get("fail_times", 2)):
                raise ModelError(
                    f"upstream timeout at step {step} (attempt {self.attempt})",
                    self._usage(step),
                )

        if self.shape in ("converging", "flaky"):
            if step <= len(PLAN):
                kind, target = PLAN[step - 1]
                if kind == "parse" and model == "haiku":
                    # The cheap model reads "1,420.00" as 142000 about a third of the time.
                    self.misread = random.Random(self.seed * 31).random() < 0.35
                return self._reply(model, {"type": kind, "target": target}, step)
            return self._reply(model, {"type": "final", "target": "record",
                                       "output": self._output()}, step, final=True)

        if self.shape == "bouncing":
            kind = "parse" if step % 2 else "validate"
            return self._reply(model, {"type": kind, "target": "amount"}, step)

        if self.shape == "stuck":
            return self._reply(model, {"type": "lookup", "target": "vendor"}, step)

        # drifting: always something new, never anything finished
        return self._reply(model, {"type": "explore", "target": f"field_{step}"}, step)

    def _reply(self, model: str, action: dict[str, Any], step: int,
               final: bool = False) -> dict[str, Any]:
        return {"model": model, "action": action, "usage": self._usage(step, final)}

    def _output(self) -> dict[str, Any]:
        raw = self.task.get("amount")
        try:
            amount = float(str(raw).replace(",", ""))
        except (TypeError, ValueError):
            amount = None
        if amount is not None and self.misread:
            amount = amount * 100
        return {"amount": amount, "vendor": self.task.get("vendor")}
