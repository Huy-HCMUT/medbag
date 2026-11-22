"""What each endpoint receives (…In) and sends back (…Out), and the checks on every request (FR-F-12).

The family app and the simulator only ever see these shapes as JSON.
A request that breaks a rule gets HTTP 400 with {"detail": "<what is wrong>"} and changes nothing.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field

from medbag_common.types import (
    SLOT_ORDER,
    Action,
    CellId,
    CheckResult,
    DoseRef,
    DoseState,
    Medicine,
    Settings,
    Slot,
    TrayResult,
)

# ------------------------------------------------------------------ requests


class ApproveIn(BaseModel):
    medicines: list[Medicine]  # the fields after the family corrected them (FR-P-05)
    approved_by: str  # e.g. "Daughter (Mei)"


class ConfirmFillIn(BaseModel):
    by: str


class TickIn(BaseModel):
    sim_time: datetime  # the simulator's clock


class ClearHoldIn(BaseModel):
    reason: Literal["camera_wrong", "tray_fixed"]
    by: str


class AnswerIn(BaseModel):
    confirm: bool  # True = the unsure pill is right; False = it is a wrong pill
    by: str


class RefillIn(BaseModel):
    kind: Literal["refill", "new_prescription"]


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    language: Literal["zh-TW", "en"]


# ------------------------------------------------------------------ responses


class FillOut(BaseModel):
    check_id: Optional[int]
    result: Optional[TrayResult]  # None = not all 4 markers seen: take the photo again
    view_url: Optional[str]  # the straightened tray photo
    say: str  # "fill_checked" or "cannot_check"


class PreDoseOut(BaseModel):
    dose: DoseRef
    state: DoseState  # open = remind and unlock; on_hold = stay locked, "please wait"
    result: Optional[TrayResult]  # None = no photo (click mode) or markers missing
    view_url: Optional[str]
    say: str  # "reminder", "reminder_missing_pill", "please_wait" or "already_started"
    alert_id: Optional[int] = None


class CheckOut(BaseModel):
    check_id: Optional[int]
    kind: Literal["dose", "lid"]  # lid = the lid closed when no dose was open
    result: Optional[CheckResult]  # dose checks only
    changed_cells: list[CellId] = []
    view_url: Optional[str]
    say: Optional[str]  # message key for the simulator's scripted line, None = say nothing
    alert_ids: list[int] = []


class TickOut(BaseModel):
    sim_time: datetime
    actions: list[Action]
    say: list[str]  # message keys to speak now (second reminders)


class DoseStatus(BaseModel):
    dose_id: str
    slot: Slot
    cell: CellId
    due_at: datetime
    state: DoseState
    done_at: Optional[datetime] = None
    medicines: list[dict]  # [{"medicine_id", "name", "purpose", "count"}]


class TodayOut(BaseModel):
    sim_time: Optional[datetime]
    schedule_approved: bool
    doses: list[DoseStatus]
    alerts: list[dict]
    waiting_checks: list[dict]  # unsure pills for the family to confirm (FR-F-06)
    log: list[dict]


# ------------------------------------------------------------------ checks on requests (FR-F-12)


def bad(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def check_settings(s: Settings) -> None:
    if set(s.dose_times) != set(SLOT_ORDER):
        raise bad("Give all 4 dose times: morning, noon, evening and bedtime.")
    for slot in SLOT_ORDER:
        if not HHMM.match(s.dose_times[slot]):
            raise bad(f"The {slot.value} time must look like 08:00.")
    times = [s.dose_times[slot] for slot in SLOT_ORDER]
    if times != sorted(times) or len(set(times)) != 4:
        raise bad("Dose times must be in order: morning, noon, evening, bedtime.")
    for name in ("second_reminder_min", "family_alert_min", "wrong_pill_min"):
        if getattr(s, name) <= 0:
            raise bad(f"{name} must be more than 0 minutes.")
    if s.family_alert_min <= s.second_reminder_min:
        raise bad("The family alert must come after the second reminder.")


def check_medicines(medicines: list[Medicine], approved_by: str) -> None:
    if not approved_by.strip():
        raise bad("Say who approves the schedule.")
    if not medicines:
        raise bad("The schedule needs at least one medicine.")
    ids = [m.id for m in medicines]
    if len(set(ids)) != len(ids):
        raise bad("Each medicine needs its own id.")
    for m in medicines:
        if not m.name.strip():
            raise bad(f"Medicine {m.id} needs a name.")
        if m.dose_per_time is None or not 1 <= m.dose_per_time <= 10:
            raise bad(f"{m.name}: pills each time must be between 1 and 10.")
        if not m.slots:
            raise bad(f"{m.name}: choose at least one time of day.")
        if len(set(m.slots)) != len(m.slots):
            raise bad(f"{m.name}: a time of day is listed twice.")
