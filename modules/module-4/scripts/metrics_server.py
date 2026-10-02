#!/usr/bin/env python3
"""The /metrics page: your receipts, as counters Prometheus can read.

    python3 metrics_server.py &                  # leave it running
    curl -s http://localhost:8000/metrics | grep agent_

Each run of the agent is a short process; a page served by it would
vanish when the run ends. So the agent writes its receipts to the ledger
and this small server turns them into counters on every request. Run the
agent again and the numbers grow rather than reset; that is exactly
what a counter is for, and why you can measure any window you like later.

Counters, and the labels they carry:

  agent_cost_usd_total      agent, team, model
  agent_tokens_total        agent, team, model, direction (input|output)
  agent_steps_total         agent, team
  agent_runs_total          agent, team, result
  agent_wasted_usd_total    agent, team          spend on runs that did not succeed

The run id is not a label. A label with one value per run is a
cardinality bomb; it lives in the ledger instead.

Every counter starts at zero for the agent below, before its first run.
Prometheus's increase() and rate() only count growth it has seen, so a
series that first appears already at 3 would count as 0, and cost per
success would come out as NaN. Initialise your counters to zero.
"""
from __future__ import annotations

import argparse
import time
from collections import defaultdict

from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY, CounterMetricFamily
from prometheus_client.registry import Collector

import ledger

# Series that exist from the start, at zero. Add your own agents here.
KNOWN = [("invoice-reader", "finance-ops", ["sonnet", "haiku"])]
RESULTS = ["success", "failure"]


class LedgerCollector(Collector):
    def collect(self):
        cost = CounterMetricFamily("agent_cost_usd", "Dollars spent on model calls.",
                                   labels=["agent", "team", "model"])
        tokens = CounterMetricFamily("agent_tokens", "Tokens, split by direction; they are priced differently.",
                                     labels=["agent", "team", "model", "direction"])
        steps = CounterMetricFamily("agent_steps", "Model calls.", labels=["agent", "team"])
        runs = CounterMetricFamily("agent_runs", "Runs, by how they ended.",
                                   labels=["agent", "team", "result"])
        wasted = CounterMetricFamily("agent_wasted_usd", "Dollars spent on runs that did not succeed.",
                                     labels=["agent", "team"])

        c, t, s = defaultdict(float), defaultdict(float), defaultdict(float)
        r, w = defaultdict(float), defaultdict(float)
        for agent, team, models in KNOWN:
            for model in models:
                c[(agent, team, model)] = 0.0
                for direction in ("input", "output"):
                    t[(agent, team, model, direction)] = 0.0
            s[(agent, team)] = w[(agent, team)] = 0.0
            for result in RESULTS:
                r[(agent, team, result)] = 0.0

        for call in ledger.read_calls():
            key = (call["agent"], call["team"], call["model"])
            c[key] += call["cost_usd"]
            t[key + ("input",)] += call["input_tokens"]
            t[key + ("output",)] += call["output_tokens"]
            s[(call["agent"], call["team"])] += 1

        for run in ledger.read_runs():
            r[(run["agent"], run["team"], run["result"])] += 1
            if run["result"] not in ("success", "unknown"):
                w[(run["agent"], run["team"])] += run["cost_usd"]

        for fam, values in ((cost, c), (tokens, t), (steps, s), (runs, r), (wasted, w)):
            for labels, value in values.items():
                fam.add_metric(list(labels), value)
            yield fam


def main() -> None:
    ap = argparse.ArgumentParser(description="Serve the ledger as Prometheus counters.")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    REGISTRY.register(LedgerCollector())
    start_http_server(a.port)
    print(f"serving http://localhost:{a.port}/metrics  (Ctrl-C to stop)", flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
