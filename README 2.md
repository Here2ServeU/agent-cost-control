# The Agent Cost Problem

A six-module course on bounded, visible, attributable agent spend. By Emmanuel Naweji.

You start with an agent that can spend four figures overnight while every dashboard stays green. You finish with an agent that:

- writes a receipt with four labels for every step,
- is capped per run and per day, with a behaviour you chose,
- has a switch anyone can flip to stop new work,
- detects loops, limits steps, and saves finished work so a retry does not start from zero,
- knows what a successful task actually costs,
- and is watched by a four-panel dashboard, two alerts and a weekly review.

## Modules

| # | Module | You build |
|---|---|---|
| 1 | [Why Agent Cost Is Different](module-01-why-agent-cost-is-different/) | Nothing yet: price the agent by hand and find your overnight-runaway number |
| 2 | [Making Cost Visible](module-02-making-cost-visible/) | The envelope: a receipt for every step, and counters on `localhost:8000/metrics` |
| 3 | [Budget Caps and Kill Switches](module-03-budget-caps-and-kill-switches/) | Per-run and daily caps, and a kill switch |
| 4 | [Loops, Retries, and the Cost of Failure](module-04-loops-retries-and-failure/) | Step limit, loop detection, checkpoints, the failed-run tax |
| 5 | [Cost Per Successful Task](module-05-cost-per-successful-task/) | `SUCCESS.md`, the result label, `cost_per_success.py` |
| 6 | [Operating It](module-06-operating-it/) | Four panels, burn-rate alerts, routing, the capstone |

Each module folder has a `README.md` with the steps, exercises and terms, and a `solution/` folder with the finished files for that module. Build each module yourself in the repo root; use `solution/` to check your work.

## Setup

```bash
git clone https://github.com/Here2ServeU/agent-cost-control && cd agent-cost-control
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key-here
python3 run_agent.py --input samples/normal.json --verbose
```

- Python 3.10 or newer.
- `samples/malformed.json` never stops on its own until Module 3. Always run it under `timeout 120`. macOS has no `timeout`: `brew install coreutils` and use `gtimeout`, or add `--max-seconds 120`.
- No API key? Add `--provider mock` to any command for a free offline simulator. Its numbers are estimates.
- Modules 2 and 6 use Docker for Prometheus and Grafana: `docker compose up -d`.

## What is in the repo

```
run_agent.py            the agent you build on, starting with no instrumentation
agent/                  the agent's loop, tools and prompts (you do not change these)
samples/                normal, malformed, flaky and loop records, plus 20 for batch runs
caps.json               budget caps and what happens at each (Module 3)
costctl/                the controls, by module:
  pricing.py envelope.py exporter.py     Module 2
  caps.py switch.py                      Module 3
  guards.py checkpoint.py                Module 4
  success.py report.py                   Module 5
  routing.py                             Module 6
observability/          Prometheus, Alertmanager and Grafana configuration
docker-compose.yml      exporter :8000, Prometheus :9090, Alertmanager :9093, Grafana :3000
module-0N-*/            each module's guide and solution
```
