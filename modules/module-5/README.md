# Module 5: Cost Per Successful Task

The only number that can tell you a change made things worse while spending less.

**Runtime:** ~50 min · 6 sections

## What this module covers

1. Would you pay a taxi by the mile it drove?
2. Four definitions of success, one set of runs
3. The failures go on the top
4. Saying it in the unit finance already counts in

## Install what you need

Module 2's setup (Python 3, a virtual environment, `prometheus-client`, `curl`). For
stage 4, the PromQL query, you also need **Docker Desktop** to run Prometheus. Stages 1 to
3 and 5 work without it.

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

Check with `docker --version` and `docker compose version`. Docker Desktop has to be
running (the whale icon in the menu bar or system tray) before `docker compose up` works.
Full instructions are in the [course README](../../README.md#install-the-tools).

```bash
cd modules/module-5/scripts
python3 -m venv .venv && source .venv/bin/activate     # Windows: py -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Scripts

Everything is in [`scripts/`](scripts). Run every command from inside that folder.

| File | What it is |
|---|---|
| `SUCCESS.md` | The definition of success, written down **before** any code. Replace it with yours |
| `success.py` | That definition as a function: `is_success(output)` returns true or false |
| `run_agent.py` | The module 4 agent. The `result` label now says `success` or `failure`, never `unknown` |
| `cost_per_success.py` | All spend ÷ successful runs, over a window, with the failures on top. `--compare-previous` shows movement |
| `docker-compose.yml`, `prometheus/` | Prometheus, scraping `metrics_server.py`, with the recording rule and the ratio alert |
| `samples/incomplete.json` | Finishes cleanly, no error, no loop, and the answer is missing. Still a failure |
| everything else | From modules 2 to 4, unchanged |

## Build it: five stages, run after every one

```bash
cd modules/module-5/scripts
```

**Stage 1: write your definition first.** Could a colleague apply it to ten runs and get
the same answers you would? If not, it is not specific enough yet.

```bash
cat SUCCESS.md                      # Windows: Get-Content SUCCESS.md
```

**Stage 2: write the check, and set the label.** Start the metrics page, then run a few
tasks, including the ones that fail:

```bash
python3 metrics_server.py &
python3 run_agent.py --input samples/normal.json && curl -s localhost:8000/metrics | grep result=
python3 run_agent.py --input samples/incomplete.json      # finished, and still a failure
python3 run_agent.py --input samples/malformed.json
curl -s localhost:8000/metrics | grep result=
```

Both `result="success"` and `result="failure"` should appear.

**Stage 3: the metric. This is the moment.** Make a few more runs so there is something to
divide, then:

```bash
for i in 1 2 3; do python3 run_agent.py --input samples/normal.json --quiet; done
python3 run_agent.py --input samples/drifting.json --quiet
python3 cost_per_success.py --since 7d
```

It prints spend, successes and the division, not just the answer, and the definition of
success comes with it every time. Compare cost per successful task with cost per request.
For most agents at this stage the gap is between 50% and 100%.

**Stage 4: the same calculation in PromQL.** With `metrics_server.py` still running:

```bash
docker compose up -d
```

Open http://localhost:9090/targets and wait until the `agent` target shows **UP** (about
30 seconds). Prometheus only counts growth it has seen, so the runs made before it started
are invisible to it. Make a few new runs, wait 30 seconds, then ask:

```bash
for i in 1 2 3; do python3 run_agent.py --input samples/normal.json --quiet; done
python3 run_agent.py --input samples/incomplete.json --quiet
curl -s localhost:9090/api/v1/query --data-urlencode \
  'query=sum(increase(agent_cost_usd_total[7d]))/sum(increase(agent_runs_total{result="success"}[7d]))'
```

The same number is kept up to date as the recording rule `agent:cost_per_success_usd:7d`
(in `prometheus/rules/cost_per_success.yml`). Compare it with `cost_per_success.py`, but
only over runs that Prometheus has seen: delete `ledger/` before you start Prometheus if you
want the two to match exactly. If they still do not match, check first that the two cover
the same time window.

If you get `NaN`, a counter only appeared after it already had a value, so Prometheus saw
no growth. That is why `metrics_server.py` starts every counter at zero. If you add your own
agent, add it to `KNOWN` at the top of that file.

**Stage 5: alert on the ratio, not on spend.** The rule `AgentCostPerSuccessHigh` fires
when cost per success rises above a threshold you pick from your own data. Comparing
against the previous window is what makes the number actionable:

```bash
python3 cost_per_success.py --since 7d --compare-previous
```

To see a comparison today, use short windows: `--since 10m --compare-previous`, with runs
made in both halves.

When you are done: `docker compose down`, and `kill %1` to stop the metrics server.

### On Windows (PowerShell)

Run `py metrics_server.py` in a second terminal. Then:

```powershell
py run_agent.py --input samples/normal.json; curl.exe -s localhost:8000/metrics | Select-String 'result='
py cost_per_success.py --since 7d
curl.exe -s localhost:9090/api/v1/query --data-urlencode 'query=sum(increase(agent_cost_usd_total[7d]))/sum(increase(agent_runs_total{result=\"success\"}[7d]))'
```

## Command reference

| Command | What it does |
|---|---|
| `cat SUCCESS.md` / `Get-Content SUCCESS.md` | Print your definition back |
| `… && curl -s localhost:8000/metrics \| grep result=` | Run a task, then show only the lines with the result label |
| `python3 cost_per_success.py --since 7d` | Spend, successes and the division over seven days |
| `--compare-previous` | The same figure for the window before, so you can see movement |
| `localhost:9090` | Prometheus. Port 8000 is your own metrics page |
| `/api/v1/query?query=…` | Ask Prometheus a question over HTTP and get JSON back |
| `sum(increase(agent_cost_usd_total[7d]))` | How much that counter grew over seven days, summed across labels |
| `agent_runs_total{result="success"}` | Only the successful runs: the denominator |

## Panels

`panels/` holds the finished versions of the diagrams drawn live on the iPad during this
module, so you can check your drawing against them.

---

[← Course home](../../README.md) · [← Module 4](../module-4/README.md) · [Next: Module 6 →](../module-6/README.md)
