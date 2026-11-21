"""changed_cells (Joshua). Write your code in this function; keep the name and the parameters.

What it takes in and gives back: packages/medbag_common/README.md (the function table)
and packages/medbag_common/examples/changed_cells.json (a real example).
Test:  uv run pytest packages/prep
"""

from __future__ import annotations

from medbag_common import fake_results
from medbag_common.types import CellId, TrayView


def changed_cells(before: TrayView, after: TrayView) -> list[CellId]:
    """Compartments that changed between two straightened photos.

    Pipeline 3 after the dose (SP6). Ignores small shifts in position and light (FR-C-13).
    """
    # TODO(Joshua): replace the line below with your real code.
    return fake_results.changed_cells(before, after)
