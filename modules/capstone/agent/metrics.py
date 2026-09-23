"""STEP 1 - INSTRUMENT IT.

Four labels, chosen once, on everything: agent, team, run, result.

  agent   which agent; so you can compare them
  team    who pays; so the bill has somewhere to go
  run     this specific execution; so you can find the runaway
  result  success or failure; so failures count in the numerator
          and not in the denominator

`run` is deliberately NOT a label on the counters. A label with one
value per run is a cardinality bomb; Prometheus will fall over long
before your agent does. The run id lives in the ledger, where it costs
nothing. This is the one place people get burned, so it is worth
saying out loud.
"""
from __future__ import annotations

import os

from prometheus_client import CollectorRegistry, Counter, push_to_gateway

REGISTRY = CollectorRegistry()

COST = Counter(
    "agent_cost_usd_total", "Dollars spent, ever.",
    ["agent", "team", "model"], registry=REGISTRY,
)
TOKENS = Counter(
    "agent_tokens_total", "Tokens, split by direction, because they are priced differently.",
    ["agent", "team", "model", "direction"], registry=REGISTRY,
)
STEPS = Counter(
    "agent_steps_total", "Model calls.",
    ["agent", "team"], registry=REGISTRY,
)
RUNS = Counter(
    "agent_runs_total", "Runs, by how they ended.",
    ["agent", "team", "result"], registry=REGISTRY,
)
WASTED = Counter(
    "agent_wasted_usd_total", "Dollars spent on runs that did not succeed. The failed-run tax.",
    ["agent", "team"], registry=REGISTRY,
)


class Metrics:
    def __init__(self, agent: str, team: str, model: str) -> None:
        self.agent, self.team, self.model = agent, team, model

    def record_step(self, input_tokens: int, output_tokens: int, usd: float) -> None:
        lbl = dict(agent=self.agent, team=self.team, model=self.model)
        COST.labels(**lbl).inc(usd)
        TOKENS.labels(**lbl, direction="input").inc(input_tokens)
        TOKENS.labels(**lbl, direction="output").inc(output_tokens)
        STEPS.labels(agent=self.agent, team=self.team).inc()

    def record_run(self, result: str, usd: float) -> None:
        RUNS.labels(agent=self.agent, team=self.team, result=result).inc()
        if result != "success":
            WASTED.labels(agent=self.agent, team=self.team).inc(usd)

    def push(self) -> str:
        """Short-lived jobs are not scraped; they push.

        Set PUSHGATEWAY=localhost:9091 (docker compose starts one).
        If it is not there, say so and carry on; a missing dashboard is
        not a reason to fail a run.
        """
        gw = os.environ.get("PUSHGATEWAY", "localhost:9091")
        try:
            push_to_gateway(gw, job="agent", registry=REGISTRY, timeout=2)
            return f"pushed to {gw}"
        except Exception as e:  # noqa: BLE001 - metrics must never break the agent
            return f"not pushed ({type(e).__name__}); ledger still written"
