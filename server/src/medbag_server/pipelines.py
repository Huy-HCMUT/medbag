"""The order in which the server calls everyone's functions (one function per pipeline).

Photos reach these functions through images.load_photo (upright, BGR, shrunk), never straight
from the upload. This is where the pieces fit together. Endpoints in main.py call these; each step uses the
real function or its fake result, as set in config.USE_REAL (see pick_method.py).

  1 read_label      POST /api/ocr      preprocess_label -> read_label -> check_fields
  2 fill_check      POST /api/tray     rectify -> detect_pills -> match_fill
  3 pre_dose_check  POST /api/tray     rectify -> detect_pills -> identify -> check_tray
    dose_check      POST /api/check    rectify -> changed_cells -> detect_pills -> identify -> check_dose
    lid_check       POST /api/check    rectify -> changed_cells   (lid opened when no dose is open)
  4 alerts          POST /api/events   alert_rules
  5 ask             POST /api/ask      answer
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import numpy as np
from medbag_common.types import (
    Action,
    Answer,
    CellState,
    CheckResult,
    DoseRef,
    DoseResult,
    Flag,
    LabelResult,
    LogEntry,
    RefPhoto,
    Schedule,
    Settings,
    TrayResult,
    TrayView,
)

from medbag_common.types import CellId

from .pick_method import get

HOLD_STATES = {CellState.wrong, CellState.extra, CellState.unsure, CellState.empty}  # FR-C-02


@dataclass
class Models:
    """Loaded once at start-up (main.py) and passed to the functions that need them."""

    yolo: Any = None  # YOLO26n for detect_pills
    dino: Any = None  # optional DINOv2 for fingerprints
    gemini: Any = None  # Gemini client; None when there is no key or no internet


@dataclass
class PreDoseOutcome:
    view: Optional[TrayView]  # kept as the before photo until the next dose time
    result: Optional[TrayResult]  # None = not checked (markers missing): remind as usual
    hold: bool  # True = keep the compartment locked and alert the family


# 1 ------------------------------------------------------------------------------------------


def read_label(photo: np.ndarray, models: Models) -> LabelResult:
    label = get("preprocess_label")(photo)
    if not (label.found and label.sharp):
        # set here, not by read_label: the photo never reaches Sam's code
        return LabelResult(engine="none", flags=[Flag(code="photo_unreadable",
                                                      message="No sharp label found. Please take a new photo.")])
    result = get("read_label")(label, models.gemini)
    return get("check_fields")(result)


# 2 ------------------------------------------------------------------------------------------


def fill_check(photo: np.ndarray, schedule: Schedule, refs: Optional[list[RefPhoto]], models: Models) -> Optional[TrayResult]:
    """None = markers not found: ask for a new photo.

    After the family confirms the grid, the server cuts each result.refs_to_save[i].pill.box
    out of the straightened tray and saves it with its fingerprint as a RefPhoto (FR-P-10).
    """
    view = get("rectify")(photo)
    if view is None:
        return None
    pills = get("detect_pills")(view, models.yolo)
    return get("match_fill")(view, pills, schedule, refs)


# 3 ------------------------------------------------------------------------------------------


def pre_dose_check(photo: np.ndarray, dose: DoseRef, schedule: Schedule, refs: list[RefPhoto], models: Models) -> PreDoseOutcome:
    view = get("rectify")(photo)
    if view is None:
        return PreDoseOutcome(view=None, result=None, hold=False)
    pills = [p for p in get("detect_pills")(view, models.yolo) if p.cell == dose.cell]
    matches = [get("identify")(view, p, refs) for p in pills]
    result = get("check_tray")(dose, matches, schedule)
    return PreDoseOutcome(view=view, result=result, hold=result.cells[0].state in HOLD_STATES)


def dose_check(before: Optional[TrayView], after_photo: np.ndarray, dose: DoseRef, schedule: Schedule,
               refs: list[RefPhoto], models: Models) -> CheckResult:
    """`before` = the view kept from pre_dose_check (or the last good one)."""
    after = get("rectify")(after_photo)
    if before is None or after is None:  # set here, never by check_dose
        return CheckResult(dose=dose, result=DoseResult.cannot_check, message_key="cannot_check")
    changed = get("changed_cells")(before, after)
    cells = set(changed) | {dose.cell}
    before_m = [get("identify")(before, p, refs) for p in get("detect_pills")(before, models.yolo) if p.cell in cells]
    after_m = [get("identify")(after, p, refs) for p in get("detect_pills")(after, models.yolo) if p.cell in cells]
    return get("check_dose")(dose, before_m, after_m, changed, schedule)


def lid_check(before: Optional[TrayView], after_photo: np.ndarray) -> Optional[list[CellId]]:
    """The lid closed while no dose is open (SP6 "Dose open? No", FR-C-13).

    Returns the compartments that changed (any change -> alert the family), or None when either
    photo has no markers (cannot check). check_dose is not called: there is no dose to check.
    """
    after = get("rectify")(after_photo)
    if before is None or after is None:
        return None
    return get("changed_cells")(before, after)


# 4, 5 ---------------------------------------------------------------------------------------


def alerts(log: list[LogEntry], sim_time: datetime, settings: Settings) -> list[Action]:
    return get("alert_rules")(log, sim_time, settings)


def ask(question: str, schedule: Schedule, log: list[LogEntry], language: str, models: Models) -> Answer:
    return get("answer")(question, schedule, log, language, models.gemini)
