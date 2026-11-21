"""Fake results: every agreed function, returning a fixed answer of the right shape.

The server uses these until each person's real function is ready, so the web app and the
simulator can be built now. In server/.../config.py, USE_REAL["rectify"] = True switches one
function to the real code once it passes the agreement test.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import numpy as np

from .types import (
    Action,
    Answer,
    Appearance,
    Box,
    CellId,
    CellState,
    CellStatus,
    Certainty,
    CheckResult,
    DoseRef,
    DoseResult,
    Evidence,
    ExpectedPill,
    Fingerprint,
    Flag,
    LabelResult,
    LogEntry,
    Match,
    MealTiming,
    Medicine,
    Pill,
    PreparedLabel,
    RefPhoto,
    RefToSave,
    Schedule,
    Settings,
    Slot,
    TRAY_H,
    TRAY_W,
    TrayResult,
    TrayView,
    cell_box,
)

# --- Joshua


def preprocess_label(img: np.ndarray) -> PreparedLabel:
    grey = img.mean(axis=2, keepdims=True).astype(np.uint8)
    binary = np.where(grey > 127, 255, 0).astype(np.uint8)[:, :, 0]  # one channel, 0 or 255
    return PreparedLabel(image=img, binary=binary, found=True, sharp=True, name_blurred=True)


def rectify(img: np.ndarray) -> Optional[TrayView]:
    # 7 day columns x 4 slot rows, 160 px each -> 1120 x 640 px, whatever the photo size
    image = np.zeros((TRAY_H, TRAY_W, 3), np.uint8)
    boxes = [cell_box(c) for c in range(28)]
    cells = [image[int(b.y):int(b.y + b.h), int(b.x):int(b.x + b.w)] for b in boxes]
    return TrayView(image=image, cells=cells, cell_boxes=boxes, mm_per_px=0.25)


def changed_cells(before: TrayView, after: TrayView) -> list[CellId]:
    return [1]  # Monday noon


# --- Sam


def read_label(label: PreparedLabel, gemini: Any) -> LabelResult:
    return LabelResult(
        engine="gemini" if gemini is not None else "tesseract",
        medicines=[
            Medicine(
                id="m1", name="安壓平錠 5mg", dose_per_time=1, frequency_per_day=2,
                slots=[Slot.morning], meal_timing=MealTiming.after_meal,
                appearance=Appearance(text="白色圓形錠", colour="white", shape="round"),
                evidence=[Evidence(field="frequency_per_day", source="text", snippet="每日 2 次")],
                unclear_fields=["slots"],
            )
        ],
    )


def check_fields(result: LabelResult) -> LabelResult:
    flags = list(result.flags)
    for m in result.medicines:
        if m.frequency_per_day and len(m.slots) != m.frequency_per_day:
            flags.append(Flag(medicine_id=m.id, field="slots", code="frequency_slots_mismatch",
                              message=f"每日 {m.frequency_per_day} 次 but {len(m.slots)} slot(s) ticked"))
    return result.model_copy(update={"flags": flags})


# --- Alex


def detect_pills(view: TrayView, model: Any) -> list[Pill]:
    # one pill in the middle of every compartment
    return [Pill(cell=c, box=Box(x=b.x + b.w / 2 - 20, y=b.y + b.h / 2 - 20, w=40, h=40), confidence=0.95)
            for c, b in enumerate(view.cell_boxes)]


def answer(question: str, schedule: Schedule, log: list[LogEntry], language: str, gemini: Any) -> Answer:
    return Answer(text="I cannot answer now, please ask your family.", language="en", fallback=True)


# --- Emily


def fingerprint(view: TrayView, pill: Pill, dino: Any = None) -> Fingerprint:
    return Fingerprint(colour_lab=(95.0, 0.0, 2.0), length_mm=8.0, width_mm=8.0, shape="round")


def identify(view: TrayView, pill: Pill, refs: list[RefPhoto]) -> Match:
    return Match(pill=pill, medicine_id="m1", score=0.92, certainty=Certainty.sure,
                 fingerprint=fingerprint(view, pill))


def _ok(cell: CellId, schedule: Schedule) -> CellStatus:
    return CellStatus(cell=cell, state=CellState.ok, expected=schedule.cells.get(cell, []), found=[])


def match_fill(view: TrayView, pills: list[Pill], schedule: Schedule,
               refs: Optional[list[RefPhoto]] = None) -> TrayResult:
    first = next((p for p in pills if schedule.cells.get(p.cell)), None)
    refs_to_save = [] if first is None else [
        RefToSave(pill=first, medicine_id=schedule.cells[first.cell][0].medicine_id,
                  fingerprint=fingerprint(view, first))]
    return TrayResult(cells=[_ok(c, schedule) for c in range(28)], refs_to_save=refs_to_save)


def check_tray(dose: DoseRef, matches: list[Match], schedule: Schedule) -> TrayResult:
    found = [m for m in matches if m.pill.cell == dose.cell]
    return TrayResult(cells=[_ok(dose.cell, schedule).model_copy(update={"found": found})])


def check_dose(dose: DoseRef, before: list[Match], after: list[Match], changed: list[CellId],
               schedule: Schedule) -> CheckResult:
    taken = [m for m in before if m.pill.cell == dose.cell]
    return CheckResult(dose=dose, result=DoseResult.correct, taken=taken, message_key="well_done")


def alert_rules(log: list[LogEntry], sim_time: datetime, settings: Settings) -> list[Action]:
    return []
