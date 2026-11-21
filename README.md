# The Talking Medicine Bag

Computer Vision course and NCCU USR competition, Group 11.
Plan, deadlines and status: the **USR** Google Sheet (tabs WBS, Tracker, Changelog). Documents and data: the team's Google Drive folder.

| Folder | Owner | What |
|---|---|---|
| `packages/medbag_common/` | Huy | Shared types and method signatures (interface agreement, WBS 1.3) |
| `packages/prep/` | Joshua | `preprocess_label`, `rectify`, `changed_cells` |
| `packages/label/` | Sam | `read_label`, `check_fields` |
| `packages/pills/` | Alex | `detect_pills`, `answer` |
| `packages/check/` | Emily | `fingerprint`, `identify`, `match_fill`, `check_tray`, `check_dose`, `alert_rules` |
| `server/` | Huy | FastAPI server, SQLite, family web app, bag simulator |
| `data/` | everyone | Test photos (downloaded from Drive, not committed) |

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
MEDBAG_IMPL=<your package> uv run pytest packages/medbag_common/tests   # contract test
git add . && git commit -m "[4.1] rectify with ArUco markers"
git push -u origin HEAD                             # then open a Pull Request on GitHub
```

Then update your status in the WBS tab of the USR sheet.

## Rules

- Never push to `main`; open a Pull Request. It merges when the tests pass and the folder's owner approves.
- Keep the exact function names and parameters from `packages/medbag_common/src/medbag_common/interfaces.py`. To change one, ask Huy first.
- Functions take data and return the shared types: no file paths, no printing, no global state.
- Use `uv add`, never `pip install`, so `uv.lock` stays the same for everyone.
- Never commit `.env`, photos, datasets or model weights (`*.pt`). They live on Google Drive.
- Put the WBS number in branch names, commit messages and Pull Request titles, e.g. `[4.4] fingerprint`.
