# The Agent Cost Problem

A seven-session course on why AI agents cost what they cost, and how to build one you
can leave running overnight.

An agent can spend four figures in a night while every dashboard stays green. Not because
anything broke, but because nothing in it was watching. This course fixes that, in order,
and ends with a repo where every mechanism is proven by running it with the mechanism
turned off and then turned on.

```bash
git clone https://github.com/Here2ServeU/agent-cost-control
cd agent-cost-control/modules/capstone
pip install -r requirements.txt
python3 verify.py
```

New machine? Start with [Install the tools](#install-the-tools) below.

---

## The course

| | Module | What it gives you | Runtime |
|---|---|---|---|
| **1** | [Why Agent Cost Is Different](modules/module-1/README.md) | Why the bill behaves unlike any other line on your invoice | ~45 min |
| **2** | [Making Cost Visible](modules/module-2/README.md) | The usage block, the envelope, and four labels | ~50 min |
| **3** | [Budget Caps and Kill Switches](modules/module-3/README.md) | Per-run and per-day caps, and the behaviour you choose | ~50 min |
| **4** | [Loops, Retries, and the Cost of Failure](modules/module-4/README.md) | Step limits, loop shapes, checkpoints, the failed-run tax | ~50 min |
| **5** | [Cost Per Successful Task](modules/module-5/README.md) | The only number that catches a change making things worse | ~50 min |
| **6** | [Operating It](modules/module-6/README.md) | Four panels, two alerts, routing, caching, a weekly habit | ~50 min |
| **★** | [**The Capstone**](modules/capstone/README.md) | All six on one agent, each one proven by running it | ~45 min |

Each module folder holds a README, a `scripts/` folder with everything that module's
hands-on section runs, and, from module 2 on, the finished versions of the diagrams drawn
live during the session (`panels/`).

---

## Scripts in every module

Every module has a `scripts/` folder that runs on its own. It holds the course agent as it
stands at the end of that module, plus the helper scripts the module's build section uses,
so you can check your own work against a version that works.

| Module | Folder | What you run |
|---|---|---|
| 1 | [`module-1/scripts`](modules/module-1/scripts) | `run_agent.py` (no instrumentation), `price_run.py` |
| 2 | [`module-2/scripts`](modules/module-2/scripts) | `run_agent.py` (the envelope), `metrics_server.py` |
| 3 | [`module-3/scripts`](modules/module-3/scripts) | `run_agent.py` (caps), `kill_switch.py` |
| 4 | [`module-4/scripts`](modules/module-4/scripts) | `run_agent.py` (step limit, loops, checkpoints), `failed_run_tax.py` |
| 5 | [`module-5/scripts`](modules/module-5/scripts) | `SUCCESS.md`, `run_agent.py`, `cost_per_success.py`, Prometheus |
| 6 | [`module-6/scripts`](modules/module-6/scripts) | `run_agent.py` (routing), `compare_runs.py`, Prometheus + Grafana |
| ★ | [`capstone`](modules/capstone) | `verify.py`, `report.py`, the full stack |

Like the capstone, nothing calls a paid API. The model is simulated, so every script runs
offline, costs nothing and prints the same numbers every time. You do not need an API key.

---

## Install the tools

You need four things for the whole course. Install them once. Each module's README lists
only what that module adds.

| Tool | Why | Needed from |
|---|---|---|
| **Python 3.10+** | every script in the course | module 1 |
| **Git** | to clone this repo | module 1 |
| **VS Code** (or any editor and terminal) | to read the code and run commands | module 1 |
| **Docker Desktop** | to run Prometheus and Grafana | module 5 (optional), module 6, capstone |

`curl` is also used from module 2 on. It is already installed on macOS, Linux and Windows
10/11. In Windows PowerShell, type `curl.exe`, not `curl`: plain `curl` there is a
different command with the same name.

If you would rather watch than read, these two short videos go from a blank machine to Git,
Python and VS Code installed:

- **macOS**: https://youtu.be/8ZIiXg4XOY0
- **Windows**: https://youtu.be/3e2-GRBibWc

### macOS

Install [Homebrew](https://brew.sh) first if you do not have it, then:

```bash
brew install python git
brew install --cask visual-studio-code
brew install --cask docker          # Docker Desktop; open it once from Applications to finish setup
```

### Windows 10/11 (PowerShell)

`winget` is built into Windows 11 and recent Windows 10:

```powershell
winget install Python.Python.3.12
winget install Git.Git
winget install Microsoft.VisualStudioCode
winget install Docker.DockerDesktop   # restart when it asks; it turns on WSL 2 for you
```

Close and reopen PowerShell afterwards so it picks up the new commands. On Windows the
Python command is `py`, so wherever this course says `python3`, type `py`.

If PowerShell refuses to activate a virtual environment ("running scripts is disabled"),
run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git curl
sudo snap install code --classic                  # VS Code
curl -fsSL https://get.docker.com | sudo sh       # Docker Engine and the compose plugin
sudo usermod -aG docker "$USER"                   # then log out and back in
```

### Check it worked

```bash
python3 --version          # 3.10 or newer   (Windows: py --version)
git --version
code --version
docker --version           # modules 5-6 and the capstone
docker compose version
```

### Get the course and set up Python

```bash
git clone https://github.com/Here2ServeU/agent-cost-control
cd agent-cost-control
python3 -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\Activate.ps1
pip install prometheus-client             # modules 2 to 6 and the capstone
```

A virtual environment is a private box of Python packages for this project only. Your
prompt starts with `(.venv)` while you are inside it; run `deactivate` to step out.
Activate it again each time you open a new terminal.

Then open the module you are on and follow its README. Every module's commands are run
from inside that module's `scripts/` folder.

### Official pages, if you prefer to read

- Python: https://www.python.org/downloads
- Git: https://git-scm.com/downloads
- VS Code: https://code.visualstudio.com/download
- Docker Desktop: https://docs.docker.com/desktop
- Python virtual environments: https://docs.python.org/3/library/venv.html
- Grafana with Prometheus: https://grafana.com/docs/grafana/latest/fundamentals

---

## What the capstone proves

The capstone is not a summary slide. It is a runnable repo with a check that fails if any
of the six stops being true:

```
$ python3 verify.py

  1. Instrumented: cost, tokens, labels             PASS   $0.0671 / 6 steps
  2. Capped: per run and per day, deliberately      PASS   capped at $0.0446
  3. Loop caught before the cap is reached          PASS   6 steps vs 14
  4. Checkpointed: a kill wastes nothing            PASS   $0.0291 not re-paid
  5. Cost per successful task, failures on top      PASS   129% above per-request
  6. Alerted on burn rate, proven by triggering it  PASS   $9,145/mo vs $300

  All six hold.
```

Every one of those proofs works by turning the mechanism off first. That is not only how
the tests work; it is how you get this work approved. "Trust me" gets no budget. "Here is
the same run with the cap off" does.

Nothing calls a paid API. The model is simulated, so the whole repo runs offline, free and
deterministic. Swapping in a real client touches one class.

---

## The six steps, and what each one buys

| | Step | Buys you |
|---|---|---|
| 1 | Instrument it | you can see it |
| 2 | Cap it | it is bounded |
| 3 | Detect the loop | 6 steps, not 14 |
| 4 | Checkpoint | stopping is cheap |
| 5 | Cost per successful task | the true number |
| 6 | Alert on burn rate | you find out while it is happening |

Each one is close to useless alone. Instrumentation with no cap means watching the money
leave in high resolution. A cap with no checkpointing means every stop throws away work.
They only work together, and together they are boring — which is the goal. An agent nobody
has to watch is the deliverable.

The whole safety layer is under four hundred lines. It is not hard. It is just never the
thing anybody does first, because it is not the demo.

---

## The idea worth keeping

Every one of the six is a decision moved earlier. A cap is deciding what a task is worth
before it runs instead of after. A step limit is deciding how long is too long while you
are calm rather than during an incident. A definition of success is deciding what you mean
before you report a number rather than in a meeting.

None of those are hard in advance. All of them are hard at three in the morning.

That is what cost control actually is. Not cleverness — deciding early, writing it down,
and letting a machine enforce it while you sleep.

---

Built by [Emmanuel Naweji](https://github.com/Here2ServeU). Licensed under the MIT License.
