"""Which dose belongs to a moment on the simulator's clock.

A dose's window runs from its dose time until the next dose time (FR-C-08), so the bedtime
dose runs until the next morning. The compartment is the day of the week and the slot:
cell = weekday * 4 + slot (Monday = 0).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional

from medbag_common.types import SLOT_ORDER, DoseRef, Settings, Slot, cell_id


def dose_time(settings: Settings, slot: Slot) -> time:
    h, m = settings.dose_times[slot].split(":")
    return time(int(h), int(m))


def dose_ref(day: date, slot: Slot, settings: Settings) -> DoseRef:
    return DoseRef(
        dose_id=f"{day.isoformat()}-{slot.value}",
        cell=cell_id(day.weekday(), slot),
        slot=slot,
        due_at=datetime.combine(day, dose_time(settings, slot)),
    )


def current_dose(sim_time: datetime, settings: Settings) -> Optional[DoseRef]:
    """The dose whose window holds sim_time (None only before the very first morning dose)."""
    latest = None
    for day in (sim_time.date() - timedelta(days=1), sim_time.date()):
        for slot in SLOT_ORDER:
            d = dose_ref(day, slot, settings)
            if d.due_at <= sim_time:
                latest = d
    return latest


def doses_of_day(day: date, settings: Settings) -> list[DoseRef]:
    return [dose_ref(day, slot, settings) for slot in SLOT_ORDER]


def dose_from_id(dose_id: str, settings: Settings) -> DoseRef:
    """"2026-11-23-noon" -> its DoseRef."""
    day, slot = dose_id[:10], dose_id[11:]
    return dose_ref(date.fromisoformat(day), Slot(slot), settings)
