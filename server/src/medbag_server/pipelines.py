"""The order in which the server calls everyone's functions (one function per pipeline).

This is where the pieces fit together. Endpoints in main.py call these. Each function comes straight
from its owner's package; until the owner writes the real code, it returns its fake result.
Photos reach these functions through images.load_photo (upright, BGR, shrunk), never straight
from the upload.

  1 label_check     POST /api/ocr      preprocess_label -> read_label -> check_fields
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
from check import alert_rules, check_dose, check_tray, identify, match_fill
from label import check_fields, read_label
from pills import detect_pills
from prep import changed_cells, preprocess_label, rectify
from voice import answer

HOLD_STATES = {CellState.wrong, CellState.extra, CellState.unsure, CellState.empty}  # FR-C-02


@dataclass
class Models:
    """Loaded once at start-up (main.py) and passed to the functions that need them."""

    yolo: Any = None  # YOLO26n for detect_pills
    dino: Any = None  # optional DINOv2 for fingerprints
    gemini: Any = None  # Gemini client; None when there is no key or no internet


@dataclass
class FillOutcome:
    view: TrayView  # saved, so the reference crops can be cut after the family confirms
    result: TrayResult


@dataclass
class DoseOutcome:
    view: Optional[TrayView]  # the straightened after photo (None = markers missing)
    result: CheckResult


@dataclass
class LidOutcome:
    view: Optional[TrayView]
    changed: Optional[list[CellId]]  # None = cannot check (markers missing on a photo)


@dataclass
class PreDoseOutcome:
    view: Optional[TrayView]  # kept as the before photo until the next dose time
    result: Optional[TrayResult]  # None = not checked (markers missing): remind as usual
    hold: bool  # True = keep the compartment locked and alert the family


# 1 ------------------------------------------------------------------------------------------


def label_check(photo: np.ndarray, models: Models) -> LabelResult:
    label = preprocess_label(photo)
    if not (label.found and label.sharp):
        # set here, not by read_label: the photo never reaches Sam's code
        return LabelResult(engine="none", flags=[Flag(code="photo_unreadable",
                                                      message="No sharp label found. Please take a new photo.")])
    result = read_label(label, models.gemini)
    return check_fields(result)


# 2 ------------------------------------------------------------------------------------------


def fill_check(photo: np.ndarray, schedule: Schedule, refs: Optional[list[RefPhoto]], models: Models) -> Optional[FillOutcome]:
    """None = markers not found: ask for a new photo.

    After the family confirms the grid, the server cuts each result.refs_to_save[i].pill.box
    out of the straightened tray and saves it with its fingerprint as a RefPhoto (FR-P-10).
    """
    view = rectify(photo)
    if view is None:
        return None
    pills = detect_pills(view, models.yolo)
    return FillOutcome(view=view, result=match_fill(view, pills, schedule, refs))


# 3 ------------------------------------------------------------------------------------------


def pre_dose_check(photo: np.ndarray, dose: DoseRef, schedule: Schedule, refs: list[RefPhoto], models: Models) -> PreDoseOutcome:
    view = rectify(photo)
    if view is None:
        return PreDoseOutcome(view=None, result=None, hold=False)
    pills = [p for p in detect_pills(view, models.yolo) if p.cell == dose.cell]
    matches = [identify(view, p, refs) for p in pills]
    result = check_tray(dose, matches, schedule)
    return PreDoseOutcome(view=view, result=result, hold=result.cells[0].state in HOLD_STATES)


def dose_check(before: Optional[TrayView], after_photo: np.ndarray, dose: DoseRef, schedule: Schedule,
               refs: list[RefPhoto], models: Models) -> DoseOutcome:
    """`before` = the view kept from pre_dose_check (or the last good one)."""
    after = rectify(after_photo)
    if before is None or after is None:  # set here, never by check_dose
        return DoseOutcome(view=after, result=CheckResult(dose=dose, result=DoseResult.cannot_check,
                                                          message_key="cannot_check"))
    changed = changed_cells(before, after)
    cells = set(changed) | {dose.cell}
    before_m = [identify(before, p, refs) for p in detect_pills(before, models.yolo) if p.cell in cells]
    after_m = [identify(after, p, refs) for p in detect_pills(after, models.yolo) if p.cell in cells]
    return DoseOutcome(view=after, result=check_dose(dose, before_m, after_m, changed, schedule))


def lid_check(before: Optional[TrayView], after_photo: np.ndarray) -> LidOutcome:
    """The lid closed while no dose is open (SP6 "Dose open? No", FR-C-13).

    Returns the compartments that changed (any change -> alert the family), or None when either
    photo has no markers (cannot check). check_dose is not called: there is no dose to check.
    """
    after = rectify(after_photo)
    if before is None or after is None:
        return LidOutcome(view=after, changed=None)
    return LidOutcome(view=after, changed=changed_cells(before, after))


# 4, 5 ---------------------------------------------------------------------------------------


def alerts(log: list[LogEntry], sim_time: datetime, settings: Settings) -> list[Action]:
    return alert_rules(log, sim_time, settings)


def ask(question: str, schedule: Schedule, log: list[LogEntry], language: str, models: Models) -> Answer:
    return answer(question, schedule, log, language, models.gemini)
