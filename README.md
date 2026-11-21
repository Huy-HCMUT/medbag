# The Talking Medicine Bag

Computer Vision course and NCCU USR competition, Group 11.
Plan, deadlines and status: the **USR** Google Sheet (tabs WBS, Tracker, Changelog). Documents and data: the team's Google Drive folder.

## Folder map

```
medbag/
├─ packages/                  each person's code (one folder = one Python package)
│  ├─ medbag_common/          shared by everyone: data types + function list (Huy, WBS 1.3)
│  │  └─ src/medbag_common/
│  │     ├─ types.py          the shapes of the data passed between functions
│  │     ├─ interfaces.py     every function's exact name, inputs and output
│  │     └─ fake_results.py   fixed answers, used until each real function is ready
│  ├─ prep/                   Joshua: prepare the images (label cleanup, tray straightening, what changed)
│  ├─ label/                  Sam: read the prescription label (Gemini, Tesseract fallback, rule checks)
│  ├─ pills/                  Alex: find the pills in each compartment (YOLO26n)
│  ├─ voice/                  Alex: answer spoken questions (Gemini, Should)
│  └─ check/                  Emily: identify pills, fill / pre-dose / dose checks, alert rules
├─ server/                    Huy: the Python server, database, family web app and bag simulator
│  ├─ src/medbag_server/
│  │  ├─ main.py              starts the server and lists the endpoints
│  │  ├─ config.py            settings from .env, and USE_REAL (real code or fake result)
│  │  ├─ pick_method.py       gives each function's real code or its fake result
│  │  └─ db.py                SQLite tables
│  └─ web/
│     ├─ family/              family web app, opened on the phone
│     └─ sim/                 bag simulator, opened on the laptop
├─ data/                      test photos: downloaded from Drive, not in git
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
