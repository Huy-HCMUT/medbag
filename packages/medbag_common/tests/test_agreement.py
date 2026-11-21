"""Agreement tests: every function has the agreed name, parameters and return type (WBS 1.3).

Run against the fake results:  uv run pytest packages/medbag_common/tests
Run against your real code:    MEDBAG_IMPL=prep uv run pytest packages/medbag_common/tests
(MEDBAG_IMPL = your package name.) Your real functions are used; everyone else's are the fake
results, so you can test your part before the others are ready.
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

from medbag_common import fake_results, interfaces, types as T

IMPL = importlib.import_module(os.environ.get("MEDBAG_IMPL", "medbag_common.fake_results"))
REPO = Path(__file__).resolve().parents[3]
DATA = Path(os.environ.get("MEDBAG_DATA", REPO / "data" / "test_samples"))


def photo(name: str, shape=(1200, 900, 3)) -> np.ndarray:
    p = DATA / name
    if p.exists():
        import cv2  # only needed with real photos

        return cv2.imread(str(p))
    return np.zeros(shape, np.uint8)


def fn(name: str):
    """Your real function if your package has it, otherwise the fake result."""
    return getattr(IMPL, name, None) or getattr(fake_results, name)


SCHEDULE = T.make_schedule(
    [T.Medicine(id="m1", name="安壓平錠 5mg", dose_per_time=1, frequency_per_day=1, slots=[T.Slot.noon])],
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
    f = getattr(IMPL, name, None)
    if f is None:
        pytest.skip(f"{IMPL.__name__} does not own {name}")
    want = list(inspect.signature(SIGNATURES[name].__call__).parameters)[1:]  # drop self
    assert list(inspect.signature(f).parameters) == want, f"{name}: parameters must be {want}"


def test_schedule_helper():
    assert [e.medicine_id for e in SCHEDULE.cells[DOSE.cell]] == ["m1"]
    assert sum(len(v) for v in SCHEDULE.cells.values()) == 7  # noon on 7 days


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


def test_tray_pipelines():
    view = fn("rectify")(photo("tray.jpg"))
    if view is None:
        pytest.skip("markers not found on the sample photo")
    assert isinstance(view, T.TrayView) and len(view.cells) == 28 and len(view.cell_boxes) == 28

    pills = fn("detect_pills")(view, None)
    assert all(isinstance(p, T.Pill) and 0 <= p.cell < 28 for p in pills)

    fill = fn("match_fill")(view, pills, SCHEDULE, None)  # pipeline 2
    assert isinstance(fill, T.FillResult)

    matches = [fn("identify")(view, p, []) for p in pills if p.cell == DOSE.cell]
    assert all(isinstance(m, T.Match) for m in matches)
    pre = fn("check_tray")(DOSE, matches, SCHEDULE)  # pipeline 3, before the dose
    assert isinstance(pre, T.FillResult) and [c.cell for c in pre.cells] == [DOSE.cell]

    changed = fn("changed_cells")(view, view)  # pipeline 3, after the dose
    assert all(isinstance(c, int) and 0 <= c < 28 for c in changed)
    result = fn("check_dose")(DOSE, matches, [], changed, SCHEDULE)
    assert isinstance(result, T.CheckResult) and result.dose == DOSE
    T.CheckResult.model_validate_json(result.model_dump_json())


def test_alert_rules():
    actions = fn("alert_rules")([], datetime(2026, 11, 23, 12, 50), T.Settings())
    assert all(isinstance(a, T.Action) for a in actions)


def test_answer():
    a = fn("answer")("Did I take my noon pills?", SCHEDULE, [], "en", None)
    assert isinstance(a, T.Answer) and a.fallback  # no Gemini -> scripted fallback
