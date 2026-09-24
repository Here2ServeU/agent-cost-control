# Module 2: Making Cost Visible

The usage block, the envelope that captures it, and the four labels that make it answerable.

**Sections:** 6

## What this module covers

1. Every model response carries a usage block; most code throws it away
2. Wrap the call once, record it everywhere
3. Four labels: agent, team, run, result
4. Turning a number into a picture

## Install what you need

Module 1's tools (Python 3, Git, VS Code), plus:

| Adds | How |
|---|---|
| a virtual environment | built into Python 3: `python3 -m venv .venv` |
| `prometheus-client` | `pip install -r requirements.txt` |
| `curl` | already on macOS, Linux and Windows 10/11 (in PowerShell type `curl.exe`) |

```bash
# macOS / Linux
cd modules/module-2/scripts
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
which python              # should point inside .venv
```

```powershell
# Windows (PowerShell)
cd modules\module-2\scripts
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
where python              # should point inside .venv
```

If you already made a `.venv` at the top of the repo (see the
[course README](../../README.md#install-the-tools)), activate that one instead. Run
`deactivate` when you are done for the day.

## Scripts

Everything is in [`scripts/`](scripts). Run every command from inside that folder.

| File | What it is |
|---|---|
| `run_agent.py` | The module 1 agent with an envelope around the model call. It prices every call and prints the four labels. Nothing is stopped yet |
| `ledger.py` | The receipts: `ledger/calls.jsonl` (one line per call) and `ledger/runs.jsonl` (one line per run) |
| `metrics_server.py` | Serves the receipts as Prometheus counters on `http://localhost:8000/metrics` |
| `sim_model.py`, `samples/` | The simulated model and the two inputs from module 1 |

The run ID appears on every printed line and in the ledger, but it is **not** a Prometheus
label. A label with one value per run is a cardinality bomb.

## Build it: four stages, run after every one

```bash
cd modules/module-2/scripts
```

**Stage 1: catch the receipt. Stage 2: turn tokens into money. Stage 3: add the four labels.**
All three are in `envelope()` and the constants at the top of `run_agent.py`.

```bash
python3 run_agent.py --input samples/normal.json
```

Every line shows `agent`, `team`, `run` and `result`, the input and output tokens, and what
the call cost. Check that the run ID is the same on every line of one run and different
between runs. Compare the total with your module 1 hand calculation.

**Stage 4: make the counter.** Start the metrics page in the background (or in a second
terminal), then run the agent and read the page:

```bash
python3 metrics_server.py &
python3 run_agent.py --input samples/normal.json && curl -s http://localhost:8000/metrics | grep agent_cost
```

```powershell
# Windows: run the server in a second terminal, then:
py run_agent.py --input samples/normal.json; curl.exe -s http://localhost:8000/metrics | Select-String agent_cost
```

**Confirm: watch the tally grow.** Run the agent three more times and read the page after
each one. The number grows and does not reset. That is how a counter should behave, and it
is why you can measure any window you like later.

```bash
curl -s http://localhost:8000/metrics | grep agent_
```

Stop the server with `kill %1` (Windows: Ctrl-C in its terminal). Delete `ledger/` to start
again from zero.

## Command reference

| Command | What it does |
|---|---|
| `python3 run_agent.py --input samples/normal.json` | Run the agent once, instrumented |
| `--verbose` | Also print the raw usage block |
| `--max-seconds 30` | Stop the malformed input; nothing else stops it yet |
| `python3 metrics_server.py &` | Serve the counters on :8000, in the background |
| `curl -s localhost:8000/metrics` | Fetch the page, silently (`-s` hides the progress meter) |
| `\| grep agent_cost` | Keep only the lines with that text |
| `A && B` | Run B only if A succeeded |

## Panels

`panels/` holds the finished versions of the diagrams drawn live on the iPad during this
module, so you can check your drawing against them.

---

[← Course home](../../README.md) · [← Module 1](../module-1/README.md) · [Next: Module 3 →](../module-3/README.md)
