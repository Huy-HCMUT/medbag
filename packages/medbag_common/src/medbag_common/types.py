"""Shared data types for The Talking Medicine Bag (WBS 1.3, interface agreement).

Every Computer Vision method takes plain data and returns one of these models.
Images are numpy arrays in BGR (OpenCV order), uint8. They live only inside the
server process; everything that goes over HTTP or into SQLite is JSON from these models.

Compartments are numbered 0..27: cell = day * 4 + slot
  day:  0 = Monday ... 6 = Sunday
  slot: 0 = morning, 1 = noon, 2 = evening, 3 = bedtime
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------- basics

CellId = int  # 0..27


class Slot(str, Enum):
    morning = "morning"
    noon = "noon"
    evening = "evening"
    bedtime = "bedtime"


SLOT_ORDER = [Slot.morning, Slot.noon, Slot.evening, Slot.bedtime]


def cell_id(day: int, slot: Slot) -> CellId:
    """Compartment number for a day (0 = Monday) and a slot."""
    return day * 4 + SLOT_ORDER.index(slot)


class MealTiming(str, Enum):
    before_meal = "before_meal"  # 飯前
    after_meal = "after_meal"  # 飯後
    with_meal = "with_meal"  # 隨餐
    any_time = "any_time"
    unknown = "unknown"


class Box(BaseModel):
    """Axis-aligned box in pixels of the image it came from."""

    x: float
    y: float
    w: float
    h: float


class ImageModel(BaseModel):
    """Base for models that carry numpy images (never sent over HTTP)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


# --------------------------------------------------------------------------- Function 1: label


class PreparedLabel(ImageModel):
    """preprocess_label (Joshua) -> read_label (Sam)."""

    image: np.ndarray = Field(exclude=True)  # cropped, straightened, patient name blurred
    found: bool  # a label was found in the photo
    sharp: bool  # sharp enough to read; False -> the app asks for a new photo
    name_blurred: bool  # must be True before anything is sent to Gemini (FR-P-14)


class Appearance(BaseModel):
    """What the label says the pill looks like, e.g. 白色圓形錠."""

    text: str = ""  # as printed
    colour: Optional[str] = None  # "white", "orange", ...
    shape: Optional[str] = None  # "round", "oval", "capsule", ...


class Evidence(BaseModel):
    """Where a field value came from on the label."""

    field: str  # "name", "dose_per_time", "frequency_per_day", "slots", "meal_timing", "appearance"
    source: Literal["text", "icon", "tick"]
    snippet: str  # the words or icon seen, e.g. "每日 3 次" or "noon icon ticked"


class Medicine(BaseModel):
    id: str  # stable id inside one schedule, e.g. "m1"
    name: str  # e.g. "安壓平錠 5mg"
    dose_per_time: Optional[int] = None  # pills each time
    frequency_per_day: Optional[int] = None
    slots: list[Slot] = []  # read from ticks or icons; filled from frequency if missing
    meal_timing: MealTiming = MealTiming.unknown
    appearance: Appearance = Appearance()
    purpose: str = ""  # typed by the family, e.g. 降血壓 (FR-P-05)
    evidence: list[Evidence] = []
    unclear_fields: list[str] = []  # fields the reader is unsure of


class Flag(BaseModel):
    """A problem for the family to look at before approving."""

    medicine_id: Optional[str] = None
    field: Optional[str] = None
    code: Literal[
        "photo_unreadable",
        "missing_field",
        "impossible_dose",
        "frequency_slots_mismatch",
        "unclear",
        "fallback_used",
    ]
    message: str


class LabelResult(BaseModel):
    """read_label and check_fields (Sam)."""

    medicines: list[Medicine] = []
    engine: Literal["gemini", "tesseract", "none"]  # "none" = the photo could not be read
    flags: list[Flag] = []
    raw_text: str = ""  # Tesseract text, or Gemini's transcription


# --------------------------------------------------------------------------- schedule


class ExpectedPill(BaseModel):
    medicine_id: str
    count: int


class Schedule(BaseModel):
    """The approved schedule. Built by the server from an approved LabelResult."""

    medicines: list[Medicine]
    cells: dict[CellId, list[ExpectedPill]]  # what each of the 28 compartments should hold
    approved_by: str
    approved_at: datetime


# --------------------------------------------------------------------------- tray


class TrayView(ImageModel):
    """rectify (Joshua). None is returned instead when the markers are not all found."""

    image: np.ndarray = Field(exclude=True)  # straightened full tray
    cells: list[np.ndarray] = Field(exclude=True)  # 28 compartment crops, index = CellId
    cell_boxes: list[Box]  # where each crop sits in `image`
    mm_per_px: float
    lid_closed: bool  # all four markers seen (FR-C-15)


class Pill(BaseModel):
    """detect_pills (Alex): one pill on the straightened tray, with its compartment."""

    cell: CellId
    box: Box  # in pixels of TrayView.image (the straightened tray)
    confidence: float


class Fingerprint(BaseModel):
    """fingerprint (Emily)."""

    colour_lab: tuple[float, float, float]
    length_mm: float
    width_mm: float
    shape: Literal["round", "oval", "capsule", "other"]
    embedding: Optional[list[float]] = None  # DINOv2, optional


class RefPhoto(BaseModel):
    """A saved reference photo (FR-P-10). The crop file lives in the photo folder."""

    medicine_id: str
    path: str
    fingerprint: Fingerprint


class Certainty(str, Enum):
    sure = "sure"
    unsure = "unsure"
    no_match = "no_match"


class Match(BaseModel):
    """identify (Emily)."""

    pill: Pill
    medicine_id: Optional[str] = None  # None when no_match
    score: float  # 0..1, higher = more alike
    certainty: Certainty


class CellState(str, Enum):
    ok = "ok"
    wrong = "wrong"
    missing = "missing"
    extra = "extra"
    unsure = "unsure"
    empty = "empty"


class CellStatus(BaseModel):
    cell: CellId
    state: CellState
    expected: list[ExpectedPill]
    found: list[Match]
    note: str = ""  # e.g. "orange pill, label says white"


class FillResult(BaseModel):
    """match_fill (fill check, all 28) and check_tray (pre-dose, due cell) (Emily)."""

    cells: list[CellStatus]
    lookalike: list[tuple[str, str]] = []  # medicine id pairs that look too alike (FR-P-11)
    refs_to_save: list[RefPhoto] = []  # filled by match_fill; saved only after the family confirms


# --------------------------------------------------------------------------- dose check


class DoseRef(BaseModel):
    dose_id: str  # e.g. "2026-11-23-noon"
    cell: CellId
    slot: Slot
    due_at: datetime


class DoseResult(str, Enum):
    correct = "correct"
    wrong_pill = "wrong_pill"
    missing_pill = "missing_pill"  # some pills left behind
    extra_pill = "extra_pill"
    not_removed = "not_removed"
    unsure = "unsure"  # waits for the family (SP9)
    cannot_check = "cannot_check"  # markers not found


class CheckResult(BaseModel):
    """check_dose (Emily)."""

    dose: DoseRef
    result: DoseResult
    taken: list[Match] = []  # before minus after
    left: list[Match] = []  # still in the due compartment
    other_changed_cells: list[CellId] = []  # FR-C-13
    message_key: str  # scripted line id, e.g. "well_done", "put_back_yellow"


# --------------------------------------------------------------------------- alerts


class DoseState(str, Enum):
    upcoming = "upcoming"
    on_hold = "on_hold"
    open = "open"
    removed = "removed"
    taken_late = "taken_late"
    missed = "missed"


class LogEntry(BaseModel):
    at: datetime
    dose_id: str
    kind: Literal[
        "reminder", "second_reminder", "on_hold", "hold_cleared", "check", "put_back", "family_alert"
    ]
    detail: dict = {}


class Settings(BaseModel):
    """FR-F-11."""

    dose_times: dict[Slot, str] = {
        Slot.morning: "08:00",
        Slot.noon: "12:30",
        Slot.evening: "18:30",
        Slot.bedtime: "21:30",
    }
    second_reminder_min: int = 15
    family_alert_min: int = 30
    wrong_pill_min: int = 2


class Action(BaseModel):
    """alert_rules (Emily): what the server should do now."""

    kind: Literal["second_reminder", "family_alert", "mark_missed", "mark_taken_late"]
    dose_id: str
    reason: Literal["late", "wrong_pill_not_put_back", "other_compartment", "pre_dose_problem", "missed"]
    message_key: str


# --------------------------------------------------------------------------- voice (Should)


class Answer(BaseModel):
    """answer (Alex)."""

    text: str
    language: Literal["zh-TW", "en"]
    fallback: bool = False  # True = scripted "please ask your family" line


# --------------------------------------------------------------------------- helpers


def make_schedule(medicines: list[Medicine], approved_by: str, approved_at: datetime) -> Schedule:
    """Approved medicines -> Schedule with what each of the 28 compartments should hold.

    Every medicine goes into its slots on all 7 days, dose_per_time pills each (1 if unknown).
    The server calls this when the family taps Approve; tests can use it to build a schedule.
    """
    cells: dict[CellId, list[ExpectedPill]] = {c: [] for c in range(28)}
    for m in medicines:
        for slot in m.slots:
            for day in range(7):
                cells[cell_id(day, slot)].append(ExpectedPill(medicine_id=m.id, count=m.dose_per_time or 1))
    return Schedule(medicines=medicines, cells=cells, approved_by=approved_by, approved_at=approved_at)
