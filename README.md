# The Talking Medicine Bag

Computer Vision course and NCCU USR competition, Group 11.
Plan, deadlines and status: the **USR** Google Sheet (tabs WBS, Tracker, Changelog). Documents and data: the team's Google Drive folder.

## Folder map

```
medbag/
├─ packages/                  each person's code (one folder = one Python package)
│  ├─ medbag_common/          the rulebook everyone follows: data types + function list (Huy, WBS 1.3)
│  │  ├─ README.md            the function table: who, what goes in, what comes out
│  │  ├─ examples/            one real input and output per function (JSON)
│  │  ├─ src/medbag_common/
│  │  │  ├─ types.py          the shapes of the data passed between functions
│  │  │  ├─ interfaces.py     every function's exact name, inputs and output
│  │  │  └─ fake_results.py   fixed answers, used until each real function is ready
│  │  └─ tests/test_agreement.py  checks your code follows the rulebook
│  ├─ prep/                   Joshua: prepare the images (label cleanup, tray straightening, what changed)
│  ├─ label/                  Sam: read the prescription label (Gemini, Tesseract fallback, rule checks)
│  ├─ pills/                  Alex: find every pill on the straightened tray (YOLO26n)
│  ├─ voice/                  Alex: answer spoken questions (Gemini, Should)
│  └─ check/                  Emily: identify pills, fill / pre-dose / dose checks, alert rules
├─ server/                    Huy: the Python server, database, family web app and bag simulator
│  ├─ src/medbag_server/
│  │  ├─ main.py              starts the server and lists the endpoints
│  │  ├─ config.py            settings from .env, and USE_REAL (real code or fake result)
│  │  ├─ pipelines.py         the order the server calls everyone's functions
│  │  ├─ pick_method.py       gives each function's real code or its fake result
│  │  ├─ images.py            turns every uploaded phone photo upright and to the agreed size
│  │  └─ db.py                SQLite tables
│  ├─ tests/               checks that all the pieces run together
│  └─ web/
│     ├─ family/              family web app, opened on the phone
│     └─ sim/                 bag simulator, opened on the laptop
├─ data/                      test photos: downloaded from Drive, not in git
│  ├─ manifest.json           every test situation, its photo and the expected result (in git)
│  └─ test_samples/           1 label + 1 tray photo used by the agreement tests (in git)
├─ pyproject.toml             the workspace: lists every package
├─ uv.lock                    exact library versions for everyone (never edit by hand)
├─ .env.example               copy to .env and add your Gemini key (.env is never committed)
└─ .github/                   automatic tests on every Pull Request, and who reviews which folder
```

| Package | Owner | Functions |
|---|---|---|
| `prep` | Joshua | `preprocess_label`, `rectify`, `changed_cells` |
| `label` | Sam | `read_label`, `check_fields` |
| `pills` | Alex | `detect_pills` |
| `voice` | Alex | `answer` |
| `check` | Emily | `fingerprint`, `identify`, `match_fill`, `check_tray`, `check_dose`, `alert_rules` |

## The rulebook: `packages/medbag_common/`

`medbag_common` is **not** where everyone's code is collected. It is written first, by Huy, and says how every
piece must look so the pieces fit together. Your real code goes in **your own package**; nobody copies it into
`medbag_common`.

```
                medbag_common      the rulebook (Huy)
             ↗   ↗    ↑    ↖   ↖
         prep label pills voice check      your code: imports its types from medbag_common
             ↖   ↖    ↓    ↗   ↗
                   server          puts the pieces together: calls everyone's functions in order
```

It does three jobs:

1. **Read it and follow it.** The function table in `packages/medbag_common/README.md`, the rules in each docstring of
   `interfaces.py` and `examples/` tell you what your function takes in, what it gives back, and what to return for a bad photo.
2. **Import it.** Never define your own `Pill` or `TrayView`. Always `from medbag_common.types import Pill, TrayView`, so what
   Joshua's `rectify` returns goes straight into Alex's `detect_pills` and Emily's `identify`.
3. **It is checked automatically.** `tests/test_agreement.py` and CI compare your code with the rulebook. A wrong function name,
   parameter or return type turns CI red, and the Pull Request cannot be merged.

**Who changes it:** only Huy. Until Sun Nov 22, 9 pm, comment on the draft. After that it is frozen as v1.0 (tag
`interface-v1.0`). If you need a change later, ask Huy: he checks who else it affects, updates `types.py`,
`interfaces.py` and `fake_results.py`, rebuilds `schemas/` and `examples/`, and tells everyone.

**What does not change when your code is ready:** `fake_results.py` stays, because the agreement tests still use everyone
else's fake results while testing yours. What changes is the import line in your own package's `__init__.py`, and
Huy's switch for your function in `server/src/medbag_server/config.py` (`USE_REAL`).

## How the pieces fit

The server calls everyone's functions in a fixed order, one pipeline per job (`server/src/medbag_server/pipelines.py`):

| Pipeline | When | Calls, in order |
|---|---|---|
| 1 Read the label | family sends a label photo | `preprocess_label` (Joshua) → `read_label` → `check_fields` (Sam) |
| 2 Fill check | the filled box is closed | `rectify` (Joshua) → `detect_pills` (Alex) → `match_fill` (Emily) |
| 3a Pre-dose check | each dose time, lid closed | `rectify` → `detect_pills` → `identify` → `check_tray` (Emily) |
| 3b Dose check | the lid closes after the dose | `rectify` → `changed_cells` (Joshua) → `detect_pills` → `identify` → `check_dose` (Emily) |
| 3c Lid check | the lid closes when no dose is open | `rectify` → `changed_cells` (Joshua); any change alerts the family |
| 4 Alerts | every clock tick | `alert_rules` (Emily) |
| 5 Voice question | big button held (Should) | `answer` (Alex) |

Every uploaded photo first goes through `server/src/medbag_server/images.py` (upright, BGR, shrunk), so phone size does not matter.
Until your real function is ready the server uses its fake result, so every pipeline already runs.
When your agreement test passes, Huy sets your function to `True` in `server/src/medbag_server/config.py`.

## Words used here

- **Package:** one folder of Python code with its own `pyproject.toml` and libraries, e.g. `packages/prep/`.
- **Interface agreement:** the list of every function's name, inputs and output (`interfaces.py`), so everyone's code fits together.
- **Fake result:** a stand-in function that returns a fixed answer of the right shape (`fake_results.py`).
- **Agreement test:** checks that your real functions follow the interface agreement (`tests/test_agreement.py`).
- **Pull Request (PR):** asking to merge your branch into `main`; the tests run and the folder's owner reviews.

## First time

1. Install uv: macOS/Linux `curl -LsSf https://astral.sh/uv/install.sh | sh`; Windows PowerShell `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. Clone and install:
   ```bash
   git clone <repo URL> && cd medbag
   uv sync                       # installs Python 3.12 and every library from uv.lock
   cp .env.example .env          # then put your own free Gemini key from Google AI Studio in .env
   uv run pytest                 # everything should pass
   ```
3. Run the server: `uv run uvicorn medbag_server.main:app --reload --host 0.0.0.0 --port 8000`, then open http://localhost:8000/api/health

## Every day

```bash
git checkout main && git pull && uv sync           # start from the latest main
git checkout -b <name>/<WBS>-<what>                 # e.g. joshua/4.1-rectify
uv add --package <your package> <library>           # add a library to YOUR package only
MEDBAG_IMPL=<your package> uv run pytest packages/medbag_common/tests   # agreement test
git add . && git commit -m "[4.1] rectify with ArUco markers"
git push -u origin HEAD                             # then open a Pull Request on GitHub
```

Then update your status in the WBS tab of the USR sheet.

## Rules

- Never push to `main`; open a Pull Request. It merges when the tests pass and the folder's owner approves.
- Keep the exact function names and parameters from `interfaces.py`. To change one, ask Huy first.
- Functions take data and return the shared types: no file paths, no printing, no global state.
- Use `uv add`, never `pip install`, so `uv.lock` stays the same for everyone.
- Never commit `.env`, photos, datasets or model weights (`*.pt`). They live on Google Drive.
- Put the WBS number in branch names, commit messages and Pull Request titles, e.g. `[4.4] fingerprint`.
