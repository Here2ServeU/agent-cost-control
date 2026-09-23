"""The model call, simulated.

The capstone is about cost control, not about spending money to learn
cost control. This module returns realistic token usage without calling
anything, so the whole repo runs offline, for free, deterministically.

Swap `SimulatedModel.next_action` for a real API call and every other
file in this repo keeps working unchanged; that is the point of putting
the usage block behind one interface.

Three inputs, three shapes of behaviour:
  good.json       converges in a handful of steps
  malformed.json  bounces: parse, validate, parse, validate, forever
  drifting.json   never repeats itself and never finishes either
"""
from __future__ import annotations

import random
from typing import Any


class SimulatedModel:
    """Deterministic given the same task file."""

    def __init__(self, task: dict[str, Any], model: str = "sonnet") -> None:
        self.task = task
        self.model = model
        self.shape = task.get("shape", "converging")
        self.n = 0
        self.rng = random.Random(task.get("seed", 7))

    def next_action(self) -> tuple[dict[str, Any], dict[str, int]]:
        """Return (action, usage). Usage is the block you must not throw away."""
        self.n += 1
        usage = {
            "input_tokens": self.rng.randint(1200, 1900),
            "output_tokens": self.rng.randint(280, 520),
        }

        if self.shape == "converging":
            plan = [
                ("read", "input"),
                ("parse", "amount"),
                ("validate", "amount"),
                ("lookup", "vendor"),
                ("write", "record"),
            ]
            if self.n <= len(plan):
                t, tg = plan[self.n - 1]
                return {"type": t, "target": tg}, usage
            return {"type": "final", "target": "record"}, usage

        if self.shape == "bouncing":
            # The classic. It cannot parse the amount, so it validates,
            # fails, and goes back to parsing the same field. Forever.
            t, tg = [("parse", "amount"), ("validate", "amount")][self.n % 2]
            return {"type": t, "target": tg}, usage

        if self.shape == "stuck":
            return {"type": "parse", "target": "amount"}, usage

        # drifting: always something new, never anything finished
        return {"type": "explore", "target": f"field_{self.n}"}, usage
