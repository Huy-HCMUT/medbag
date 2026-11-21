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
    FillResult,
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
    Schedule,
    Settings,
    Slot,
    TrayView,
)

# --- Joshua


def preprocess_label(img: np.ndarray) -> PreparedLabel:
    return PreparedLabel(image=img, found=True, sharp=True, name_blurred=True)


def rectify(img: np.ndarray) -> Optional[TrayView]:
    h, w = 700, 400  # 7 rows (days) x 4 columns (slots), 100 px each
    cells = [np.zeros((100, 100, 3), np.uint8) for _ in range(28)]
    boxes = [Box(x=(c % 4) * 100, y=(c // 4) * 100, w=100, h=100) for c in range(28)]
    return TrayView(image=np.zeros((h, w, 3), np.uint8), cells=cells, cell_boxes=boxes,
                    mm_per_px=0.3, lid_closed=True)


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
    return Match(pill=pill, medicine_id="m1", score=0.92, certainty=Certainty.sure)


def _ok(cell: CellId, schedule: Schedule) -> CellStatus:
    return CellStatus(cell=cell, state=CellState.ok, expected=schedule.cells.get(cell, []), found=[])


def match_fill(view: TrayView, pills: list[Pill], schedule: Schedule,
               refs: Optional[list[RefPhoto]] = None) -> FillResult:
    return FillResult(cells=[_ok(c, schedule) for c in range(28)])


def check_tray(dose: DoseRef, matches: list[Match], schedule: Schedule) -> FillResult:
    return FillResult(cells=[_ok(dose.cell, schedule)])


def check_dose(dose: DoseRef, before: list[Match], after: list[Match], changed: list[CellId],
               schedule: Schedule) -> CheckResult:
    taken = [m for m in before if m.pill.cell == dose.cell]
    return CheckResult(dose=dose, result=DoseResult.correct, taken=taken, message_key="well_done")


def alert_rules(log: list[LogEntry], sim_time: datetime, settings: Settings) -> list[Action]:
    return []
