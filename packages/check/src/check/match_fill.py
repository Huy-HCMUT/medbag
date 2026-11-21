"""match_fill (Emily). Write your code in this function; keep the name and the parameters.

What it takes in and gives back: packages/medbag_common/README.md (the function table)
and packages/medbag_common/examples/match_fill.json (a real example).
Test:  uv run pytest packages/check
"""

from __future__ import annotations

from typing import Optional

from medbag_common import fake_results
from medbag_common.types import Pill, RefPhoto, Schedule, TrayResult, TrayView


def match_fill(
    view: TrayView,
    pills: list[Pill],
    schedule: Schedule,
    refs: Optional[list[RefPhoto]] = None,
) -> TrayResult:
    """Fill check of all 28 compartments right after filling (Pipeline 2, SP3).

    There are no reference photos yet on the first fill (refs = None), so it compares with
    the schedule and the label's appearance (and with refs on a refill), compares the same
    medicine across days and warns about look-alikes. refs_to_save lists one good pill per
    medicine (pill + medicine id + fingerprint); it writes no files. The server cuts the
    crops and saves them only after the family confirms the grid.
    """
    # TODO(Emily): replace the line below with your real code.
    return fake_results.match_fill(view, pills, schedule, refs)
