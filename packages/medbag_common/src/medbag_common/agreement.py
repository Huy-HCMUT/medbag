"""The agreement check: does a package follow the rulebook? (WBS 1.3)

Every package's tests call check_package("<package>"). It uses that package's functions and the fake
results for everyone else's, runs every pipeline with them and checks names, parameters and outputs.
So you can test your part before the others are ready:  uv run pytest packages/<your package>
"""

from __future__ import annotations

import importlib
import inspect
import os
from datetime import datetime
from pathlib import Path

import numpy as np

from . import fake_results, interfaces
from . import types as T

REPO = Path(__file__).resolve().parents[4]
SAMPLES = Path(os.environ.get("MEDBAG_DATA", REPO / "data" / "test_samples"))  # label.jpg, tray.jpg

SIGNATURES = {
    "preprocess_label": interfaces.PreprocessLabel, "rectify": interfaces.Rectify,
    "changed_cells": interfaces.ChangedCells, "read_label": interfaces.ReadLabel,
    "check_fields": interfaces.CheckFields, "detect_pills": interfaces.DetectPills,
    "answer": interfaces.AnswerQuestion, "fingerprint": interfaces.FingerprintPill,
    "identify": interfaces.Identify, "match_fill": interfaces.MatchFill,
    "check_tray": interfaces.CheckTray, "check_dose": interfaces.CheckDose,
    "alert_rules": interfaces.AlertRules,
}

SCHEDULE = T.make_schedule(
    [T.Medicine(id="m1", name="Test tablet 5mg", dose_per_time=1, frequency_per_day=1, slots=[T.Slot.noon])],
    approved_by="family", approved_at=datetime(2026, 11, 23, 9, 0),
)
DOSE = T.DoseRef(dose_id="2026-11-23-noon", cell=1, slot=T.Slot.noon, due_at=datetime(2026, 11, 23, 12, 30))


def photo(name: str) -> np.ndarray:
    """A sample photo from data/test_samples/, or a blank one until it is there."""
    p = SAMPLES / name
    if p.exists():
        import cv2

        return cv2.imread(str(p))
    return np.zeros((1200, 900, 3), np.uint8)


def check_package(package: str) -> None:
    """Raise AssertionError with a clear message if `package` breaks the rulebook."""
    mod = importlib.import_module(package)

    def fn(name):  # this package's function if it has one, else the fake result
        return getattr(mod, name, None) or getattr(fake_results, name)

    # 1 names and parameters
    for name, proto in SIGNATURES.items():
        f = getattr(mod, name, None)
        if f is None:
            continue
        want = list(inspect.signature(proto.__call__).parameters)[1:]  # drop self
        got = list(inspect.signature(f).parameters)
        assert got == want, f"{name}: parameters must be {want}, yours are {got}"

    # 2 pipeline 1: the label
    label = fn("preprocess_label")(photo("label.jpg"))
    assert isinstance(label, T.PreparedLabel), "preprocess_label must return a PreparedLabel"
    if label.found and label.sharp:
        assert label.name_blurred, "preprocess_label: the patient name must be blurred (FR-P-14)"
        assert label.image.ndim == 3, "PreparedLabel.image must be a colour image (H x W x 3)"
        assert label.binary.ndim == 2 and set(np.unique(label.binary)) <= {0, 255}, \
            "PreparedLabel.binary must be one channel with only 0 and 255"
        result = fn("read_label")(label, None)  # no Gemini -> Tesseract
        assert isinstance(result, T.LabelResult), "read_label must return a LabelResult"
        assert result.engine == "tesseract", "read_label with gemini=None must use Tesseract"
        checked = fn("check_fields")(result)
        assert isinstance(checked, T.LabelResult), "check_fields must return a LabelResult"
        T.LabelResult.model_validate_json(checked.model_dump_json())

    # 3 pipelines 2 and 3: the tray
    view = fn("rectify")(photo("tray.jpg"))
    if view is None:
        return  # markers not found on the sample photo: nothing more to check with it
    assert isinstance(view, T.TrayView), "rectify must return a TrayView or None"
    assert view.image.shape == (T.TRAY_H, T.TRAY_W, 3), "TrayView.image must be 640 x 1120 x 3"
    assert len(view.cells) == 28 and all(c.shape == (T.CELL_PX, T.CELL_PX, 3) for c in view.cells), \
        "TrayView.cells must be 28 images of 160 x 160 x 3"
    assert view.cell_boxes == [T.cell_box(c) for c in range(28)], "TrayView.cell_boxes[c] must be cell_box(c)"

    pills = fn("detect_pills")(view, None)
    assert all(isinstance(p, T.Pill) and 0 <= p.cell < 28 for p in pills), "detect_pills must return Pills, cell 0-27"

    fill = fn("match_fill")(view, pills, SCHEDULE, None)
    assert isinstance(fill, T.TrayResult) and len(fill.cells) == 28, "match_fill must return a TrayResult with 28 cells"
    assert all(isinstance(r, T.RefToSave) for r in fill.refs_to_save), "refs_to_save must be RefToSave"

    matches = [fn("identify")(view, p, []) for p in pills if p.cell == DOSE.cell]
    assert all(isinstance(m, T.Match) and isinstance(m.fingerprint, T.Fingerprint) for m in matches), \
        "identify must return a Match with its fingerprint"
    pre = fn("check_tray")(DOSE, matches, SCHEDULE)
    assert isinstance(pre, T.TrayResult) and [c.cell for c in pre.cells] == [DOSE.cell], \
        "check_tray must return a TrayResult with only the due compartment"

    changed = fn("changed_cells")(view, view)
    assert all(isinstance(c, int) and 0 <= c < 28 for c in changed), "changed_cells must return numbers 0-27"
    result = fn("check_dose")(DOSE, matches, [], changed, SCHEDULE)
    assert isinstance(result, T.CheckResult) and result.dose == DOSE, "check_dose must return a CheckResult for this dose"
    assert result.result != T.DoseResult.cannot_check, "check_dose never returns cannot_check (the server sets it)"
    T.CheckResult.model_validate_json(result.model_dump_json())

    # 4, 5 alerts and voice
    actions = fn("alert_rules")([], datetime(2026, 11, 23, 12, 50), T.Settings())
    assert all(isinstance(a, T.Action) for a in actions), "alert_rules must return a list of Action"
    a = fn("answer")("Did I take my noon pills?", SCHEDULE, [], "en", None)
    assert isinstance(a, T.Answer) and a.fallback, "answer with gemini=None must give the scripted fallback"
