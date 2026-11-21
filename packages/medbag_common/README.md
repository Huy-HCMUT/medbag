# medbag_common · interface agreement (WBS 1.3)

Shared data types and the exact method signatures for The Talking Medicine Bag.
Draft v0.1 by Huy, 2026-11-21. **Please comment by Sun Nov 22**; after that the names and fields are frozen
and changes go through Huy.

## What each person delivers

Each owner's package exposes these exact function names. `interfaces.py` has the full signature and rules for each.

| Method | Owner | In | Out | Pipeline |
|---|---|---|---|---|
| `preprocess_label(img)` | Joshua | label photo | `PreparedLabel` (found, sharp, name blurred) | 1 |
| `read_label(label, gemini)` | Sam | `PreparedLabel`, Gemini client or None | `LabelResult` (engine = gemini or tesseract) | 1 |
| `check_fields(result)` | Sam | `LabelResult` | same, with `flags` | 1 |
| `rectify(img)` | Joshua | tray photo | `TrayView` (28 crops, mm per px, lid closed) or `None` | 2, 3 |
| `detect_pills(cell_img, cell, model)` | Alex | one compartment crop | `list[Pill]` | 2, 3 |
| `fingerprint(crop, mm_per_px, dino)` | Emily | pill crop | `Fingerprint` | 2, 3 |
| `identify(cell_img, pill, mm_per_px, refs)` | Emily | one pill, her reference photos | `Match` (sure, unsure, no_match) | 3 |
| `match_fill(view, pills, schedule, refs)` | Emily | all 28 compartments | `FillResult` (grid, look-alikes, refs to save) | 2 |
| `check_tray(view, pills, dose, schedule, refs)` | Emily | due compartment, lid closed | `FillResult` with one cell | 3 (before) |
| `changed_cells(before, after)` | Joshua | two `TrayView`s | `list[CellId]` | 3 (after) |
| `check_dose(dose, before, after, changed, schedule)` | Emily | matches before and after | `CheckResult` | 3 (after) |
| `alert_rules(log, sim_time, settings)` | Emily | dose log, simulator time | `list[Action]` | 4 |
| `answer(question, schedule, log, language, gemini)` | Alex | question text | `Answer` | 5 (Should) |

Compartments are numbered `cell = day * 4 + slot` (day 0 = Monday; slot 0 morning, 1 noon, 2 evening, 3 bedtime).

## Rules

- Take data, return a model from `medbag_common.types`. No file paths, no printing, no global state.
- The server loads YOLO26n, DINOv2 and the Gemini client once and passes them in. The API key never leaves the server.
- A bad photo is not an exception: return the "could not" value (`found=False`, `None`, `cannot_check`).
- Holding a compartment, clearing a hold and sending alerts are the server's decisions. Methods only return results.

## Try it

```bash
uv sync
uv run pytest packages/medbag_common/tests                    # against the stubs
MEDBAG_IMPL=prep uv run pytest packages/medbag_common/tests   # against Joshua's package, etc.
```

`stubs.py` holds fixed answers with the same signatures; the server uses them until each real method passes
its contract test. `schemas/` has a JSON Schema per type for anyone who prefers JSON.
