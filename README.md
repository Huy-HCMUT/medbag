# The Talking Medicine Bag

Computer Vision course and NCCU USR competition, Group 11.
Plan, deadlines and status: the **USR** Google Sheet (tabs WBS, Tracker). Documents and data: the team's Google Drive folder.

## Start here

You only work in **your own folder**. Each of your functions already has its own file: open it and write your code
inside the function. Until you do, it returns a fake answer, so the whole app already runs.

| Who | Your folder | Your files (one per function) |
|---|---|---|
| Joshua | `packages/prep/src/prep/` | `preprocess_label.py`, `rectify.py`, `changed_cells.py` |
| Sam | `packages/label/src/label/` | `read_label.py`, `check_fields.py` |
| Alex | `packages/pills/src/pills/` and `packages/voice/src/voice/` | `detect_pills.py`, `answer.py` |
| Emily | `packages/check/src/check/` | `fingerprint.py`, `identify.py`, `match_fill.py`, `check_tray.py`, `check_dose.py`, `alert_rules.py` |

**What goes in and what comes out of your function:** the table in [`packages/medbag_common/README.md`](packages/medbag_common/README.md),
and a real example in `packages/medbag_common/examples/<your function>.json`.

### Once

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/):
   - macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. Get the code and install everything:
   ```bash
   git clone https://github.com/Huy-HCMUT/medbag.git
   cd medbag
   uv sync
   uv run pytest
   ```
   `uv sync` installs Python 3.12 and every library. `uv run pytest` should end with "passed".

### For each task

```bash
git switch main
git pull
git switch -c joshua/4.1-rectify          # a new branch: your name / WBS number - what
# ... write your code ...
uv run pytest packages/prep               # test your package (use your own folder name)
git add .
git commit -m "[4.1] rectify with ArUco markers"
git push -u origin HEAD
```

Then open GitHub, click **Compare & pull request**, and wait for the green tick and a review.
Need a library? `uv add --package prep opencv-python` (your package name, then the library).

### Rules

- Keep your function's **name and parameters** exactly as they are. `uv run pytest` tells you if something does not fit.
- Use the shared types, never your own: `from medbag_common.types import TrayView, Pill`.
- Never commit `.env`, photos, datasets or model files (`*.pt`). They live on Google Drive.
- Do not edit other people's folders, `packages/medbag_common/` or `server/`. Need a change there? Ask Huy.
- Stuck for more than 30 minutes? Ask in the group chat.

---

## How it fits together

`packages/medbag_common/` is **the rulebook** (Huy): the shared data types and every function's name, inputs and output.
It is not where code is collected. Everyone's code imports its types from it, and the server calls everyone's functions in order:

```
                medbag_common      the rulebook (Huy)
             ↗   ↗    ↑    ↖   ↖
         prep label pills voice check      each person's code
             ↖   ↖    ↓    ↗   ↗
                   server          calls everyone's functions in order (Huy)
```

Each package's test (`uv run pytest packages/<name>`) runs `check_package`: it uses your functions and everyone else's
fake answers, runs every pipeline and checks names, parameters and outputs. So you can test your part before the others are ready.
The same tests run on GitHub for every Pull Request.

The order of the calls (`server/src/medbag_server/pipelines.py`):

| Pipeline | When | Calls, in order |
|---|---|---|
| 1 Read the label | the family sends a label photo | `preprocess_label` (Joshua) → `read_label` → `check_fields` (Sam) |
| 2 Fill check | the filled box is closed | `rectify` (Joshua) → `detect_pills` (Alex) → `match_fill` (Emily) |
| 3a Pre-dose check | each dose time, lid closed | `rectify` → `detect_pills` → `identify` → `check_tray` (Emily) |
| 3b Dose check | the lid closes after the dose | `rectify` → `changed_cells` (Joshua) → `detect_pills` → `identify` → `check_dose` (Emily) |
| 3c Lid check | the lid closes when no dose is open | `rectify` → `changed_cells` (Joshua); any change alerts the family |
| 4 Alerts | every clock tick | `alert_rules` (Emily) |
| 5 Voice question | big button held (Should) | `answer` (Alex) |

## Folder map

```
medbag/
├─ packages/
│  ├─ medbag_common/   the rulebook: types, function list, fake answers, examples (Huy)
│  ├─ prep/            Joshua: label cleanup, tray straightening, what changed
│  ├─ label/           Sam: read the prescription label (Gemini, Tesseract fallback, rule checks)
│  ├─ pills/           Alex: find every pill on the straightened tray (YOLO26n)
│  ├─ voice/           Alex: answer spoken questions (Gemini, Should)
│  └─ check/           Emily: identify pills, fill / pre-dose / dose checks, alert rules
├─ server/             Huy: server (FastAPI), database (SQLite), family web app, bag simulator
├─ data/               test situations (manifest.json); the photos themselves are on Drive
├─ .github/            tests on GitHub, who reviews which folder, Pull Request form
├─ pyproject.toml      lists every package (uv workspace)
├─ uv.lock             exact library versions for everyone (never edit by hand)
└─ .env.example        copy to .env for the Gemini key (only to run the server with Gemini)
```

Run the server: `uv run uvicorn medbag_server.main:app --reload --host 0.0.0.0 --port 8000`, then open http://localhost:8000/api/health.
For Gemini, copy `.env.example` to `.env` and add a free key from Google AI Studio.

## Words used here

- **Package:** one folder of Python code with its own libraries, e.g. `packages/prep/`.
- **Fake answer:** what your function returns until you write it: a fixed answer of the right shape.
- **Branch:** your own copy of the code for one task, so `main` stays working.
- **Pull Request (PR):** asking to put your branch into `main`. The tests run on GitHub and the folder's owner reviews.
