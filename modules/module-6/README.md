# Module 6: Operating It

Four dashboard panels, two alerts, model routing, caching, and the fifteen-minute weekly habit.

**Runtime:** ~50 min · 6 sections

## What this module covers

1. Four panels, each titled with a question somebody asks out loud
2. Alert on the rate, not the total: two windows, two speeds
3. Routing and caching, in that order, and the danger in each
4. The review that needs a name against it

## Install what you need

Module 2's setup (Python 3, a virtual environment, `prometheus-client`, `curl`), plus:

| Adds | How |
|---|---|
| **Docker Desktop** | runs Prometheus and Grafana |
| **Grafana** | comes in the compose file; nothing to install |
| a browser | Grafana on http://localhost:3000, Prometheus on http://localhost:9090 |
| a calendar invite | for the weekly review; there is no script for that part |

```bash
# macOS
brew install --cask docker            # then open Docker Desktop once from Applications
```

```powershell
# Windows (PowerShell); restart when it asks
winget install Docker.DockerDesktop
```

```bash
# Linux (Ubuntu/Debian)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"       # then log out and back in
```

Check with `docker --version` and `docker compose version`, and make sure Docker Desktop
is running. Full instructions are in the [course README](../../README.md#install-the-tools).

```bash
cd modules/module-6/scripts
python3 -m venv .venv && source .venv/bin/activate     # Windows: py -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Scripts

Everything is in [`scripts/`](scripts). Run every command from inside that folder.

| File | What it is |
|---|---|
| `run_agent.py` | The finished agent: instrumented, capped, bounded, checkpointed, labelled, and now routed. `--route STEP` sends one step type to a cheaper model. `--repeat` and `--batch` run a batch |
| `compare_runs.py` | Two batches compared on cost **and** quality. If quality moved at all, it tells you to revert |
| `docker-compose.yml` | Prometheus and Grafana |
| `prometheus/rules/burn_rate.yml` | The fast (1 hour) and slow (24 hour) burn-rate alerts, plus the failed-run tax |
| `prometheus/rules/cost_per_success.yml` | From module 5 |
| `grafana/` | The four panels, already provisioned, each titled with a question |
| `cost_per_success.py`, `failed_run_tax.py` | From modules 4 and 5 |
| everything else | From modules 2 to 5, unchanged |

## Build it: four stages, then the capstone

```bash
cd modules/module-6/scripts
```

**Setup: start the metrics page, Prometheus and Grafana.**

```bash
python3 metrics_server.py &
docker compose up -d prometheus grafana
```

Prometheus answers on :9090. Grafana opens on http://localhost:3000 (admin / admin), and
the dashboard **Agent Cost: Four Panels** is already there. Make some runs so it has data:

```bash
python3 run_agent.py --input samples/normal.json --repeat 10 --batch warmup --quiet
python3 run_agent.py --input samples/malformed.json
```

**Stage 1: the four panels.** Test every query in the terminal before putting it in a
panel. Debugging PromQL inside a panel is miserable.

```bash
curl -s localhost:9090/api/v1/query --data-urlencode 'query=sum(rate(agent_cost_usd_total[1h]))*3600'
curl -s localhost:9090/api/v1/query --data-urlencode \
  'query=sum(increase(agent_cost_usd_total[24h])) / sum(increase(agent_runs_total{result="success"}[24h]))'
```

| Panel title (the question) | Query |
|---|---|
| What are we spending? | `sum(rate(agent_cost_usd_total[1h])) * 3600` |
| What is it buying us? | `sum(increase(agent_cost_usd_total[24h])) / sum(increase(agent_runs_total{result="success"}[24h]))` |
| Who is spending it? | `sum by (team) (increase(agent_cost_usd_total[30d]))` |
| How much is wasted? | `sum(rate(agent_wasted_usd_total[6h])) / sum(rate(agent_cost_usd_total[6h]))` |

**Stage 2: the two alerts, and proving one fires.** Both are in
`prometheus/rules/burn_rate.yml`. The fast one looks at the last hour and pages someone.
The slow one looks at 24 hours and becomes a ticket. To prove the fast one works, run the
runaway with the caps turned off, deliberately:

```bash
MAX_STEPS=600 python3 run_agent.py --input samples/malformed.json \
  --no-caps --no-loop-detect --pace 0.5 --quiet &
```

Watch http://localhost:9090/alerts. `AgentBurnRateFast` goes to pending, then firing,
within a couple of minutes.

One thing you may notice first: the simulated model answers instantly, so even the warm-up
batches look like a burst to a one-hour window, and the fast alert can go pending before
the runaway starts. A real model takes seconds per call and would not do that. The runaway
is what pushes the projection into the thousands of dollars a month. **Then stop it** (`kill %2`, or Ctrl-C) and never leave it
running unattended. The caps come back on by themselves: `--no-caps` only affects that one
run.

**Stage 3: route one step type.** Choose the most mechanical step, send only that step to
the cheaper model, run twenty tasks, and compare both cost and quality with the previous
twenty:

```bash
python3 run_agent.py --input samples/normal.json --repeat 20 --batch baseline --quiet
python3 run_agent.py --input samples/normal.json --repeat 20 --batch routed --route read --route lookup --quiet
python3 compare_runs.py --before baseline --after routed
```

That gives you two numbers: how much you saved, and whether anything got worse. Now try
routing a step that is not mechanical:

```bash
python3 run_agent.py --input samples/normal.json --repeat 20 --batch parse-routed --route parse --quiet
python3 compare_runs.py --before baseline --after parse-routed
```

It is cheaper, and a third of the answers are now wrong. If quality moved at all, put that
step back on the expensive model. The saving is not worth an argument about quality.

**Stage 4: the capstone. The bill that never arrived.** Run module 1's malformed input
against everything you have built:

```bash
python3 run_agent.py --input samples/malformed.json
curl -s localhost:9090/api/v1/query --data-urlencode 'query=sum(increase(agent_cost_usd_total[1h]))'
```

It stops in three calls for about three cents. Put that beside your module 1 extrapolation.

When you are done:

```bash
docker compose down
kill %1                       # the metrics server
```

### On Windows (PowerShell)

Run `py metrics_server.py` in one terminal and the runaway in another:

```powershell
$env:MAX_STEPS="600"; py run_agent.py --input samples/malformed.json --no-caps --no-loop-detect --pace 0.5 --quiet
# Ctrl-C once the alert fires, then:
Remove-Item Env:MAX_STEPS
```

Use `curl.exe` instead of `curl` for the queries.

## Caching and the weekly review

Neither has a script, because both are decisions rather than code:

- **The caching test:** would two different people asking this question get the same
  answer? If yes, it is safe to cache. If no, never cache it. If you are unsure, do not
  cache. Build the cache key from the whole call, including the system prompt.
- **The weekly review:** fifteen minutes, same slot every week, one named owner, with the
  Grafana link in the calendar invite. Four questions: what changed, who spent, what was
  wasted, and did an alert fire.

## Command reference

| Command | What it does |
|---|---|
| `docker compose up -d prometheus grafana` | Start both containers in the background |
| `curl -s localhost:9090/api/v1/query --data-urlencode 'query=…'` | Ask Prometheus a question, with the query safely encoded |
| `sum(rate(agent_cost_usd_total[1h]))*3600` | Spend per second over the last hour, turned into spend per hour |
| `--no-caps` | This run only: module 3 caps off, to prove the alert fires |
| `--route read` | Send that step type to the cheaper model (repeatable) |
| `--repeat 20 --batch NAME` | Twenty different tasks of the same kind, tagged for comparison |
| `python3 compare_runs.py --before baseline --after routed` | Cost and quality, side by side |
| `docker compose down` | Stop the containers |

## Panels

`panels/` holds the finished versions of the diagrams drawn live on the iPad during this
module, so you can check your drawing against them.

---

[← Course home](../../README.md) · [← Module 5](../module-5/README.md) · [Next: The Capstone →](../capstone/README.md)
