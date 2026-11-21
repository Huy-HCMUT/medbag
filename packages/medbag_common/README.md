# medbag_common · interface agreement (WBS 1.3)

Shared data types and the exact function signatures for The Talking Medicine Bag.
Draft v0.2 by Huy, 2026-11-22. **Please comment by Sun Nov 22, 9 pm**; after that the names and fields are frozen
and changes go through Huy.

## What each person delivers

Each person's package exports these exact function names. `interfaces.py` has the full rules for each one.

| Function | Owner | In | Out | Pipeline |
|---|---|---|---|---|
| `preprocess_label(img)` | Joshua | label photo | `PreparedLabel` (found, sharp, name blurred) | 1 |
| `read_label(label, gemini)` | Sam | `PreparedLabel`, Gemini client or None | `LabelResult` (engine = gemini, tesseract or none) | 1 |
| `check_fields(result)` | Sam | `LabelResult` | same, with `flags` | 1 |
| `rectify(img)` | Joshua | tray photo | `TrayView` (straightened tray, 28 compartments, mm per px, lid closed) or `None` | 2, 3 |
| `detect_pills(view, model)` | Alex | `TrayView` | `list[Pill]`, each with its compartment | 2, 3 |
| `match_fill(view, pills, schedule, refs)` | Emily | all pills after filling | `FillResult` (grid of 28, look-alikes, refs to save) | 2 |
| `identify(view, pill, refs)` | Emily | one `Pill`, her reference photos | `Match` (medicine, sure / unsure / no_match) | 3 |
| `check_tray(dose, matches, schedule)` | Emily | matches in the due compartment, lid closed | `FillResult` with one compartment | 3 (before the dose) |
| `changed_cells(before, after)` | Joshua | two `TrayView`s | `list[CellId]` | 3 (after the dose) |
| `check_dose(dose, before, after, changed, schedule)` | Emily | matches before and after | `CheckResult` | 3 (after the dose) |
| `alert_rules(log, sim_time, settings)` | Emily | dose log, simulator time | `list[Action]` | 4 |
| `answer(question, schedule, log, language, gemini)` | Alex (`voice`) | question text | `Answer` | 5 (Should) |
| `fingerprint(view, pill, dino)` | Emily | one `Pill` | `Fingerprint` (colour, size in mm, shape) | inside Emily's code only |

How the server chains them: `server/src/medbag_server/pipelines.py` (one short function per pipeline).

## Conventions

- Compartments: `cell = day * 4 + slot` (day 0 = Monday; slot 0 morning, 1 noon, 2 evening, 3 bedtime). `cell_id(day, slot)` does it.
- Photos are numpy arrays, BGR, uint8 (what `cv2.imread` gives).
- A `Pill`'s box is in pixels of the straightened tray (`TrayView.image`); `TrayView.cell_boxes[i]` is compartment i.
- `make_schedule(medicines, approved_by, approved_at)` builds the 28-compartment `Schedule`; use it in your tests.

## Rules

- Take data, return a model from `medbag_common.types`. No file paths, no printing, no global state.
- The server loads YOLO26n, DINOv2 and the Gemini client once and passes them in. The API key never leaves the server.
- A bad photo is not an exception: return the "could not" value (`found=False`, `None`, `cannot_check`).
- Holding a compartment, clearing a hold and sending alerts are the server's decisions. Functions only return results.

## Try it

```bash
uv sync
uv run pytest packages/medbag_common/tests                    # against the fake results
MEDBAG_IMPL=prep uv run pytest packages/medbag_common/tests   # your real functions + everyone else's fake results
```

`fake_results.py` holds fixed answers with the same signatures; the server uses them until each real function
passes its agreement test (`tests/test_agreement.py`). `schemas/` has a JSON Schema per type for anyone who prefers JSON.

## Changes

- **v0.2 (Nov 22):** `detect_pills` runs once on the whole straightened tray (the YOLO annotations in WBS 2.5 are on
  whole-tray photos). `identify` and `fingerprint` take the `TrayView` and a `Pill`. `check_tray` and `check_dose` take
  `Match` lists from `identify`. `match_fill` takes a plain list of pills. New helper `make_schedule`; the label engine can be `none`.
- **v0.1 (Nov 21):** first draft.
