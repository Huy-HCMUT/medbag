# medbag_common · interface agreement (WBS 1.3)

Shared data types and the exact function signatures for The Talking Medicine Bag: **the rulebook everyone follows**.
Draft v0.3 by Huy, 2026-11-22. **Please comment by Sun Nov 22, 9 pm**; after that the names and fields are frozen
and changes go through Huy.

> **This folder is not where your code goes.** Write your functions in your own package (`packages/prep/`, `label/`,
> `pills/`, `voice/` or `check/`) and import the types from here: `from medbag_common.types import TrayView, Pill`.
> Only Huy edits this folder. Need a change? Ask Huy, so everyone else's code keeps fitting.

| File | What it is for | Do you edit it? |
|---|---|---|
| `README.md` (this file) | The function table: who makes each function, what goes in, what comes out | No, read it |
| `examples/<function>.json` | One real input and output per function | No, read it |
| `src/medbag_common/types.py` | Every data type passed between functions (`Pill`, `TrayView`, `Match`, ...) | No, import it |
| `src/medbag_common/interfaces.py` | Each function's exact name and parameters, with its rules in the docstring | No, follow it |
| `src/medbag_common/fake_results.py` | Fixed answers with the right shape, used until your real function is ready | No |
| `tests/test_agreement.py` | Checks your real functions against this rulebook | No, run it |
| `schemas/`, `export_schemas.py`, `export_examples.py` | JSON versions of the types and examples, rebuilt by Huy | No |

## What each person delivers

Each person's package exports these exact function names. `interfaces.py` has the full rules for each one, and
`examples/<function>.json` shows a real input and output for every function. In the table, **image** means a numpy
array (BGR, uint8, size shown as height × width × 3); everything else is numbers, text or lists of them.

| # | Function | Owner | In | Out | Pipeline |
|---|---|---|---|---|---|
| 1 | `preprocess_label(img)` | Joshua | `img`: label photo (image, any size) | `PreparedLabel`: `image` colour label for Gemini (image); `binary` black and white label for Tesseract (image, 1 channel, 0 or 255); `found`, `sharp`, `name_blurred` (true / false) | 1 |
| 2 | `read_label(label, gemini)` | Sam | `label`: `PreparedLabel` (only when found and sharp); `gemini`: client or None | `LabelResult`: `medicines` (name, pills each time, times a day, slots, meal timing, appearance, evidence, unclear fields); `engine` = gemini or tesseract; `flags`; `raw_text` | 1 |
| 3 | `check_fields(result)` | Sam | `result`: `LabelResult` | same `LabelResult` with problems added to `flags` (missing_field, impossible_dose, frequency_slots_mismatch, ...) | 1 |
| 4 | `rectify(img)` | Joshua | `img`: tray photo (image, any size) | `TrayView`: `image` straightened tray (image, always 640 × 1120 × 3); `cells` 28 crops (images, 160 × 160 × 3); `cell_boxes` 28 boxes in px; `mm_per_px` (number). Or `None`: the 4 markers were not all seen (lid open, a marker covered, bad photo) | 2, 3 |
| 5 | `detect_pills(view, model)` | Alex | `view`: `TrayView`; `model`: YOLO26n | list of `Pill`: `cell` (0–27), `box` (x, y, w, h in px of `view.image`), `confidence` (0–1). Every pill on the tray, found once per photo | 2, 3 |
| 6 | `match_fill(view, pills, schedule, refs)` | Emily | `view`; `pills` from 5; `schedule`; `refs`: saved reference photos, or None on the first fill | `TrayResult`: `cells` 28 × `CellStatus` (ok / wrong / missing / extra / unsure / empty, expected, found, note); `lookalike` medicine pairs; `refs_to_save` one `RefToSave` per medicine (pill, medicine id, fingerprint). Writes no files | 2 |
| 7 | `identify(view, pill, refs)` | Emily | `view`; one `Pill`; `refs`: list of `RefPhoto` (uses only their fingerprints) | `Match`: `pill`, `medicine_id` (None if no_match), `score` (0–1), `certainty` (sure / unsure / no_match), `fingerprint` of this pill | 3 |
| 8 | `check_tray(dose, matches, schedule)` | Emily | `dose`: the dose now due; `matches`: 7 for each pill in `dose.cell`; `schedule` | `TrayResult` with one `CellStatus`, for `dose.cell` | 3 (before the dose) |
| 9 | `changed_cells(before, after)` | Joshua | two `TrayView`s | list of compartment numbers (0–27) that changed | 3 (after the dose, and lid closed with no dose open) |
| 10 | `check_dose(dose, before, after, changed, schedule)` | Emily | `dose`: the open dose; `before`, `after`: 7 for each pill in the changed compartments; `changed` from 9; `schedule` | `CheckResult`: `result` (correct / wrong_pill / missing_pill / extra_pill / not_removed / unsure); `taken`, `left` (lists of `Match`); `other_changed_cells`; `message_key` (text id of the spoken line) | 3 (after the dose) |
| 11 | `alert_rules(log, sim_time, settings)` | Emily | `log`: list of `LogEntry`; `sim_time`: simulator clock; `settings` (minutes for each rule) | list of `Action`: kind (second_reminder / family_alert / mark_missed / mark_taken_late), dose id, reason, message key | 4 |
| 12 | `answer(question, schedule, log, language, gemini)` | Alex (`voice`) | `question` (text); `schedule`; `log`; `language` (zh-TW or en); `gemini` client or None | `Answer`: `text`, `language`, `fallback` (true = scripted "please ask your family" line) | 5 (Should) |
| – | `fingerprint(view, pill, dino)` | Emily | `view`; one `Pill`; DINOv2 or None | `Fingerprint`: `colour_lab` (3 numbers), `length_mm`, `width_mm`, `shape`, optional `embedding`. Called inside 6 and 7 only | inside Emily's code |

**Set by the server, not by these functions** (`server/src/medbag_server/pipelines.py`):

- `engine = "none"` with a `photo_unreadable` flag, when `preprocess_label` gives `found` or `sharp` = false. `read_label` is not called.
- `result = cannot_check`, when `rectify` returns `None` for the before or the after photo. `check_dose` is not called.
- **Lid closed when no dose is open** (`lid_check`): only `rectify` and `changed_cells` run; any changed compartment alerts the family.
- Saving reference photos: after the family confirms, the server cuts each `refs_to_save` pill out of `view.image` and saves it with its fingerprint as a `RefPhoto`. The same happens for an unsure pill the family confirms (it uses `Match.fingerprint`).

## Conventions

- Compartments: `cell = day * 4 + slot` (day 0 = Monday; slot 0 morning, 1 noon, 2 evening, 3 bedtime). `cell_id(day, slot)` does it.
- **Photo sizes.** Phones send different sizes, sometimes sideways. The server's `images.load_photo` turns every upload upright
  (EXIF), makes it BGR uint8 and shrinks it: longest side at most **2000 px for labels** and **1600 px for trays**; smaller photos
  stay as they are. So your function must accept any size up to that.
- **The straightened tray is always 1120 × 640 px:** 7 day columns (Monday on the left) × 4 slot rows (morning on top), 160 px
  per compartment. Compartment c is at x = (c // 4) × 160, y = (c % 4) × 160; `cell_box(c)` gives its box. Constants: `TRAY_W`,
  `TRAY_H`, `CELL_PX`.
- A `Pill`'s box is in pixels of the straightened tray (`TrayView.image`); `TrayView.cell_boxes[i]` is compartment i.
- `make_schedule(medicines, approved_by, approved_at)` builds the 28-compartment `Schedule`; use it in your tests.

## Rules

- Take data, return a model from `medbag_common.types`. No file paths, no saving files, no printing, no global state.
- The server loads YOLO26n, DINOv2 and the Gemini client once and passes them in. The API key never leaves the server.
- A bad photo is not an exception: return the "could not" value (`found=False` or `sharp=False`, `None` from `rectify`).
- Holding a compartment, clearing a hold, saving photos and sending alerts are the server's decisions. Functions only return results.

## Try it

```bash
uv sync
uv run pytest packages/medbag_common/tests                    # against the fake results
MEDBAG_IMPL=prep uv run pytest packages/medbag_common/tests   # your real functions + everyone else's fake results
```

`fake_results.py` holds fixed answers with the same signatures; the server uses them until each real function
passes its agreement test (`tests/test_agreement.py`). `schemas/` has a JSON Schema per type and `examples/` one input and output per function, for anyone who prefers JSON.
After changing `types.py` or `fake_results.py`, run `uv run python packages/medbag_common/export_schemas.py` and
`uv run python packages/medbag_common/export_examples.py`; CI fails if they are out of date.

## Changes

- **v0.3 (Nov 22):** One table with what each input and output is. `PreparedLabel.binary` (black and white label for
  Tesseract, made by Joshua). `TrayView.lid_closed` removed: `rectify` returns `None` when the markers are not all seen.
  The straightened tray is always 1120 × 640 px (7 day columns × 4 slot rows, 160 px each). `FillResult` renamed `TrayResult`.
  `refs_to_save` is now a list of `RefToSave` (pill, medicine id, fingerprint): `match_fill` writes no files. `Match` carries
  the pill's `fingerprint`, so a confirmed unsure pill can become a reference. `engine = none` and `cannot_check` are set by the
  server only. New: server `lid_check` (lid closed when no dose is open), `images.load_photo`, `examples/`.
- **v0.2 (Nov 22):** `detect_pills` runs once on the whole straightened tray (the YOLO annotations in WBS 2.5 are on
  whole-tray photos). `identify` and `fingerprint` take the `TrayView` and a `Pill`. `check_tray` and `check_dose` take
  `Match` lists from `identify`. `match_fill` takes a plain list of pills. New helper `make_schedule`; the label engine can be `none`.
- **v0.1 (Nov 21):** first draft.
