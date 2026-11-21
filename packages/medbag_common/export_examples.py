"""Write one example per function into examples/: what goes in and what comes out.

The values come from fake_results.py, so they have exactly the agreed shape. Images are shown as
"<image H x W x 3>" (a numpy array of that shape, BGR uint8) because they are never turned into JSON.
Run after changing types.py or fake_results.py:  uv run python packages/medbag_common/export_examples.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from medbag_common import fake_results as F
from medbag_common import types as T


def show(x):
    """Any value -> JSON-friendly value, with images described instead of dumped."""
    if isinstance(x, np.ndarray):
        return "<image " + " x ".join(map(str, x.shape)) + ">"
    if isinstance(x, BaseModel):
        out = {}
        for name in type(x).model_fields:
            out[name] = show(getattr(x, name))
        return out
    if isinstance(x, dict):
        items = list(x.items())
        if len(items) > 4 and all(isinstance(k, int) for k, _ in items):  # e.g. Schedule.cells (28)
            shown = {str(k): show(v) for k, v in items[:2]}
            shown["..."] = f"{len(items)} compartments in all"
            return shown
        return {str(k): show(v) for k, v in items}
    if isinstance(x, (list, tuple)):
        if len(x) > 4 and all(isinstance(i, np.ndarray) for i in x):
            return [show(x[0]), f"... {len(x)} images in all"]
        if len(x) > 4 and all(isinstance(i, BaseModel) for i in x):
            return [show(i) for i in x[:2]] + [f"... {len(x)} items in all"]
        return [show(i) for i in x]
    if isinstance(x, datetime):
        return x.isoformat()
    if hasattr(x, "value"):  # Enum
        return x.value
    return x


label_photo = np.zeros((2000, 1500, 3), np.uint8)
tray_photo = np.zeros((1200, 1600, 3), np.uint8)
prepared = F.preprocess_label(label_photo)
label_result = F.read_label(prepared, None)
# the family fixed the slots (每日 2 次 -> morning and noon) before tapping Approve
approved = [m.model_copy(update={"slots": [T.Slot.morning, T.Slot.noon], "unclear_fields": []})
            for m in label_result.medicines]
schedule = T.make_schedule(approved, "family", datetime(2026, 11, 23, 9, 0))
view = F.rectify(tray_photo)
pills = F.detect_pills(view, None)
pill = pills[1]
dose = T.DoseRef(dose_id="2026-11-23-noon", cell=1, slot=T.Slot.noon, due_at=datetime(2026, 11, 23, 12, 30))
refs = [T.RefPhoto(medicine_id="m1", path="photos/ref_m1_0.png", fingerprint=F.fingerprint(view, pill))]
match = F.identify(view, pill, refs)
settings = T.Settings()
log = [T.LogEntry(at=datetime(2026, 11, 23, 12, 30), dose_id=dose.dose_id, kind="reminder")]

EXAMPLES = {
    "preprocess_label": ({"img": label_photo}, prepared),
    "read_label": ({"label": prepared, "gemini": None}, label_result),
    "check_fields": ({"result": label_result}, F.check_fields(label_result)),
    "rectify": ({"img": tray_photo}, view),
    "detect_pills": ({"view": view, "model": "<YOLO26n model>"}, pills),
    "fingerprint": ({"view": view, "pill": pill, "dino": None}, F.fingerprint(view, pill)),
    "match_fill": ({"view": view, "pills": pills, "schedule": schedule, "refs": None},
                   F.match_fill(view, pills, schedule, None)),
    "identify": ({"view": view, "pill": pill, "refs": refs}, match),
    "check_tray": ({"dose": dose, "matches": [match], "schedule": schedule}, F.check_tray(dose, [match], schedule)),
    "changed_cells": ({"before": view, "after": view}, F.changed_cells(view, view)),
    "check_dose": ({"dose": dose, "before": [match], "after": [], "changed": [1], "schedule": schedule},
                   F.check_dose(dose, [match], [], [1], schedule)),
    "alert_rules": ({"log": log, "sim_time": datetime(2026, 11, 23, 12, 50), "settings": settings},
                    [T.Action(kind="second_reminder", dose_id=dose.dose_id, reason="late", message_key="second_reminder")]),
    "answer": ({"question": "Did I take my noon pills?", "schedule": schedule, "log": log, "language": "en",
                "gemini": None}, F.answer("Did I take my noon pills?", schedule, log, "en", None)),
}

out_dir = Path(__file__).parent / "examples"
out_dir.mkdir(exist_ok=True)
for name, (inputs, output) in EXAMPLES.items():
    doc = {"function": name, "in": show(inputs), "out": show(output)}
    (out_dir / f"{name}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(name)
