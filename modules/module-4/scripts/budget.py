"""MODULE 3 - THE CAPS AND THE SWITCH.

Per run and per day, and a behaviour at the edge chosen on purpose.
A cap without a chosen behaviour is not a cap; it is a surprise.

  stop   stop starting new steps, return a clear "capped" result,
         keep nothing. The right first choice for most people.
  drain  stop starting new steps, save the work done so far, exit
         cleanly. The right answer once there is work worth keeping.
  kill   stop now. Only when one more step costs more than the work.

Settings are environment variables, so you can change them without
touching code:

  RUN_BUDGET_USD     per-run cap                  (default 0.50)
  DAILY_BUDGET_USD   per-day cap, all runs        (default 10.00)
  ON_BREACH          stop | drain | kill          (default stop)
  AGENT_ENABLED      false refuses all new runs   (default true)

The daily total lives in ledger/day-YYYY-MM-DD.jsonl so it survives
between runs; a single run does not know what happened earlier today.
Every charge is appended as its own line rather than rewriting a total,
so several runs at once cannot overwrite each other's spend. In
production this is a Redis INCRBYFLOAT or a database row. The logic is
the same.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

STATE = Path("ledger")
FIRST_STEP_ESTIMATE_USD = 0.01          # before the first call there is no "last step" to go by
SWITCH_FILE = STATE / "agent_enabled.json"


class BudgetExceeded(Exception):
    """Named, so the top of the agent can catch exactly this case."""

    def __init__(self, scope: str, spent: float, cap: float, env: str) -> None:
        super().__init__(
            f"{scope} budget reached: ${spent:.4f} spent against a ${cap:.2f} cap. "
            f"The run was stopped before its next model call. "
            f"Raise {env} if this task is worth more.")
        self.scope, self.spent, self.cap = scope, spent, cap


class AgentDisabled(Exception):
    pass


def _env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


class Budget:
    def __init__(self) -> None:
        self.per_run = _env_float("RUN_BUDGET_USD", 0.50)
        self.per_day = _env_float("DAILY_BUDGET_USD", 10.00)
        self.on_breach = os.environ.get("ON_BREACH", "stop").lower()
        if self.on_breach not in ("stop", "drain", "kill"):
            raise SystemExit(f"ON_BREACH must be stop, drain or kill; got {self.on_breach!r}")
        self.run_spend = 0.0
        self.last_step = FIRST_STEP_ESTIMATE_USD

    # --- the daily total, kept outside the process ------------------------
    @property
    def day_file(self) -> Path:
        return STATE / f"day-{time.strftime('%Y-%m-%d')}.jsonl"

    def day_spend(self) -> float:
        if not self.day_file.exists():
            return 0.0
        return sum(float(line) for line in self.day_file.read_text().split() if line)

    def _add_to_day(self, usd: float) -> None:
        STATE.mkdir(parents=True, exist_ok=True)
        with self.day_file.open("a") as f:     # append, never rewrite: safe with concurrent runs
            f.write(f"{usd:.8f}\n")

    # --- the checks -------------------------------------------------------
    def before_run(self) -> None:
        """Checked before any work at all. Refusing early costs nothing."""
        if not agent_enabled():
            raise AgentDisabled(
                "agent is switched off (AGENT_ENABLED=false or kill_switch.py off); "
                "no new runs are started. Runs already in flight are allowed to finish.")
        if self.day_spend() >= self.per_day:
            raise BudgetExceeded("daily", self.day_spend(), self.per_day, "DAILY_BUDGET_USD")

    def before_call(self) -> None:
        """Checked before every model call.

        The next step will cost about what the last one did, so do not
        start a step the budget cannot finish. This is what keeps spend
        under the cap rather than one step over it.
        """
        if self.run_spend + self.last_step > self.per_run:
            raise BudgetExceeded("per-run", self.run_spend, self.per_run, "RUN_BUDGET_USD")
        if self.day_spend() + self.last_step > self.per_day:
            raise BudgetExceeded("daily", self.day_spend(), self.per_day, "DAILY_BUDGET_USD")

    def charge(self, usd: float) -> None:
        """After every call. The money is already spent; write it down."""
        self.run_spend += usd
        self.last_step = usd
        self._add_to_day(usd)


def agent_enabled() -> bool:
    """The kill switch: an environment variable, or a file anyone can flip."""
    if os.environ.get("AGENT_ENABLED", "true").lower() in ("false", "0", "off", "no"):
        return False
    if SWITCH_FILE.exists():
        return json.loads(SWITCH_FILE.read_text()).get("enabled", True)
    return True
