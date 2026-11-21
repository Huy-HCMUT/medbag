"""check_tray (Emily). Write your code in this function; keep the name and the parameters.

What it takes in and gives back: packages/medbag_common/README.md (the function table)
and packages/medbag_common/examples/check_tray.json (a real example).
Test:  uv run pytest packages/check
"""

from __future__ import annotations

from medbag_common import fake_results
from medbag_common.types import DoseRef, Match, Schedule, TrayResult


def check_tray(dose: DoseRef, matches: list[Match], schedule: Schedule) -> TrayResult:
    """Pre-dose check of the due compartment, lid closed (Pipeline 3 before the dose, SP4).

    `matches` = identify() for every pill in dose.cell. Returns one CellStatus for
    dose.cell: ok, wrong, missing, extra, unsure or empty. The server holds the dose for
    wrong, extra, unsure or empty.
    """
    # TODO(Emily): replace the line below with your real code.
    return fake_results.check_tray(dose, matches, schedule)
