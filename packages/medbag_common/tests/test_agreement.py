"""Agreement tests: every function has the agreed name, parameters and return type (WBS 1.3).

Run against the fake results:  uv run pytest packages/medbag_common/tests
Run against your real code:    MEDBAG_IMPL=prep uv run pytest packages/medbag_common/tests
(MEDBAG_IMPL = your package name; functions it does not have are skipped.)
Put two sample photos in data/test_samples/: label.jpg and tray.jpg. Until then, blank images are used.
"""

from __future__ import annotations

import importlib
import inspect
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from medbag_common import interfaces, types as T

IMPL = importlib.import_module(os.environ.get("MEDBAG_IMPL", "medbag_common.fake_results"))
DATA = Path(os.environ.get("MEDBAG_DATA", "data/test_samples"))


def photo(name: str, shape=(1200, 900, 3)) -> np.ndarray:
    p = DATA / name
    if p.exists():
        import cv2  # only needed with real photos

        return cv2.imread(str(p))
    return np.zeros(shape, np.uint8)


def fn(name: str):
    f = getattr(IMPL, name, None)
    if f is None:
        pytest.skip(f"{IMPL.__name__} has no {name}")
    return f


SCHEDULE = T.Schedule(
    medicines=[T.Medicine(id="m1", name="安壓平錠 5mg", dose_per_time=1, frequency_per_day=1,
                          slots=[T.Slot.noon])],
    cells={c: [T.ExpectedPill(medicine_id="m1", count=1)] for c in range(1, 28, 4)},
    approved_by="family", approved_at=datetime(2026, 11, 23, 9, 0),
)
DOSE = T.DoseRef(dose_id="2026-11-23-noon", cell=1, slot=T.Slot.noon, due_at=datetime(2026, 11, 23, 12, 30))

SIGNATURES = {
    "preprocess_label": interfaces.PreprocessLabel, "rectify": interfaces.Rectify,
    "changed_cells": interfaces.ChangedCells, "read_label": interfaces.ReadLabel,
    "check_fields": interfaces.CheckFields, "detect_pills": interfaces.DetectPills,
    "answer": interfaces.AnswerQuestion, "fingerprint": interfaces.FingerprintPill,
    "identify": interfaces.Identify, "match_fill": interfaces.MatchFill,
    "check_tray": interfaces.CheckTray, "check_dose": interfaces.CheckDose,
    "alert_rules": interfaces.AlertRules,
}


@pytest.mark.parametrize("name", SIGNATURES)
def test_signature(name):
    f = fn(name)
    want = list(inspect.signature(SIGNATURES[name].__call__).parameters)[1:]  # drop self
    assert list(inspect.signature(f).parameters) == want


def test_label_pipeline():
    label = fn("preprocess_label")(photo("label.jpg"))
    assert isinstance(label, T.PreparedLabel)
    if label.found and label.sharp:
        assert label.name_blurred
        result = fn("read_label")(label, None)  # no Gemini -> Tesseract path
        assert isinstance(result, T.LabelResult) and result.engine == "tesseract"
        checked = fn("check_fields")(result)
        assert isinstance(checked, T.LabelResult)
        T.LabelResult.model_validate_json(checked.model_dump_json())  # survives JSON


def test_tray_pipeline():
    view = fn("rectify")(photo("tray.jpg"))
    if view is None:
        pytest.skip("markers not found on the sample photo")
    assert isinstance(view, T.TrayView) and len(view.cells) == 28 and len(view.cell_boxes) == 28
    pills = fn("detect_pills")(view.cells[1], 1, None)
    assert all(isinstance(p, T.Pill) and p.cell == 1 for p in pills)
    matches = [fn("identify")(view.cells[1], p, view.mm_per_px, []) for p in pills]
    assert all(isinstance(m, T.Match) for m in matches)
    fill = fn("match_fill")(view, {1: pills}, SCHEDULE, None)
    assert isinstance(fill, T.FillResult)
    pre = fn("check_tray")(view, pills, DOSE, SCHEDULE, [])
    assert isinstance(pre, T.FillResult) and [c.cell for c in pre.cells] == [DOSE.cell]
    changed = fn("changed_cells")(view, view)
    assert all(isinstance(c, int) and 0 <= c < 28 for c in changed)
    result = fn("check_dose")(DOSE, {1: matches}, {1: []}, changed, SCHEDULE)
    assert isinstance(result, T.CheckResult) and result.dose == DOSE


def test_alert_rules():
    actions = fn("alert_rules")([], datetime(2026, 11, 23, 12, 50), T.Settings())
    assert all(isinstance(a, T.Action) for a in actions)


def test_answer():
    a = fn("answer")("Did I take my noon pills?", SCHEDULE, [], "en", None)
    assert isinstance(a, T.Answer) and a.fallback  # no Gemini -> scripted fallback
