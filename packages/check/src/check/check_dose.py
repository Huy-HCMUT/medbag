"""check_dose (Emily). Write your code in this function; keep the name and the parameters.

What it takes in and gives back: packages/medbag_common/README.md (the function table)
and packages/medbag_common/examples/check_dose.json (a real example).
Test:  uv run pytest packages/check
"""

from __future__ import annotations

from medbag_common import fake_results
from medbag_common.types import CellId, CheckResult, DoseRef, Match, Schedule


def check_dose(
    dose: DoseRef,
    before: list[Match],
    after: list[Match],
    changed: list[CellId],
    schedule: Schedule,
) -> CheckResult:
    """Dose check after the lid closes (Pipeline 3 after the dose, SP6).

    `before` / `after` = identify() for every pill in the changed compartments, in the
    before and after photos. taken = before minus after in dose.cell. Any changed cell
    other than dose.cell goes into other_changed_cells. An unsure pill gives result = unsure.
    result is never cannot_check: the server sets that itself when a photo has no markers.
    A lid opened and closed when no dose is open is also the server's job (changed_cells only).
    """
    # TODO(Emily): replace the line below with your real code.
    return fake_results.check_dose(dose, before, after, changed, schedule)
