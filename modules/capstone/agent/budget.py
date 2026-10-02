"""STEP 2: CAP IT. Per run, per day, and say what happens at the edge.

A cap without a chosen behaviour is not a cap; it is a surprise. There
are three honest answers and you pick one on purpose:

  drain  stop starting new steps, let the current one finish, save
         everything, exit cleanly. Right answer almost always.
  stop   finish the step, mark the run capped, do not save.
  kill   stop immediately, mid-step. Only when the cost of one more
         step is worse than losing the work.

The daily cap is kept in a small file so it survives restarts. In
production that file is a row in a database; the logic is the same.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path


class BudgetExceeded(Exception):
    def __init__(self, scope: str, spent: float, cap: float) -> None:
        super().__init__(f"{scope} cap reached: ${spent:.4f} of ${cap:.2f}")
        self.scope, self.spent, self.cap = scope, spent, cap


@dataclass
class Budget:
    per_run_usd: float
    per_day_usd: float
    on_breach: str = "drain"            # drain | stop | kill
    state_dir: Path = Path("ledger")
    enabled: bool = True

    def __post_init__(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.run_spend = 0.0

    # --- daily ledger -------------------------------------------------
    @property
    def _day_file(self) -> Path:
        return self.state_dir / f"day-{time.strftime('%Y-%m-%d')}.json"

    def day_spend(self) -> float:
        if not self._day_file.exists():
            return 0.0
        return json.loads(self._day_file.read_text()).get("usd", 0.0)

    def _add_day(self, usd: float) -> float:
        total = round(self.day_spend() + usd, 8)
        self._day_file.write_text(json.dumps({"usd": total}))
        return total

    # --- the check ----------------------------------------------------
    def charge(self, usd: float) -> None:
        """Called after every step. Raises when a cap is reached.

        Note the order: charge first, then check. You have already spent
        the money; pretending otherwise is how caps leak.
        """
        self.run_spend = round(self.run_spend + usd, 8)
        day_total = self._add_day(usd)
        if not self.enabled:
            return
        if self.run_spend >= self.per_run_usd:
            raise BudgetExceeded("per-run", self.run_spend, self.per_run_usd)
        if day_total >= self.per_day_usd:
            raise BudgetExceeded("per-day", day_total, self.per_day_usd)

    def would_exceed(self, estimate_usd: float) -> bool:
        """Cheap pre-flight, so the last step does not blow through the cap."""
        return self.enabled and (self.run_spend + estimate_usd) >= self.per_run_usd
