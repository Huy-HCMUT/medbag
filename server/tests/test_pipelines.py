"""Integration test: every pipeline runs end to end, and every package exports what the server needs."""

import importlib
from datetime import datetime

import numpy as np
from medbag_common import types as T

from medbag_server import pipelines as P
from medbag_server.pick_method import OWNER_PACKAGE

PHOTO = np.zeros((1200, 900, 3), np.uint8)
MODELS = P.Models()
SCHEDULE = T.make_schedule(
    [T.Medicine(id="m1", name="安壓平錠 5mg", dose_per_time=1, frequency_per_day=1, slots=[T.Slot.noon])],
    approved_by="family", approved_at=datetime(2026, 11, 23, 9, 0),
)
DOSE = T.DoseRef(dose_id="2026-11-23-noon", cell=1, slot=T.Slot.noon, due_at=datetime(2026, 11, 23, 12, 30))


def test_every_package_exports_its_functions():
    for name, package in OWNER_PACKAGE.items():
        assert callable(getattr(importlib.import_module(package), name, None)), f"{package} must export {name}"


def test_read_label():
    assert isinstance(P.read_label(PHOTO, MODELS), T.LabelResult)


def test_fill_check():
    assert isinstance(P.fill_check(PHOTO, SCHEDULE, None, MODELS), T.FillResult)


def test_pre_dose_then_dose_check():
    pre = P.pre_dose_check(PHOTO, DOSE, SCHEDULE, [], MODELS)
    assert pre.view is not None and not pre.hold
    result = P.dose_check(pre.view, PHOTO, DOSE, SCHEDULE, [], MODELS)
    assert isinstance(result, T.CheckResult)


def test_dose_check_without_before_photo():
    assert P.dose_check(None, PHOTO, DOSE, SCHEDULE, [], MODELS).result == T.DoseResult.cannot_check


def test_alerts_and_ask():
    assert P.alerts([], datetime(2026, 11, 23, 12, 50), T.Settings()) == []
    assert P.ask("Did I take my noon pills?", SCHEDULE, [], "en", MODELS).fallback
