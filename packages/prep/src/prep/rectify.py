"""rectify (Joshua). Write your code in this function; keep the name and the parameters.

What it takes in and gives back: packages/medbag_common/README.md (the function table)
and packages/medbag_common/examples/rectify.json (a real example).
Test:  uv run pytest packages/prep
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from medbag_common import fake_results
from medbag_common.types import TrayView


def rectify(img: np.ndarray) -> Optional[TrayView]:
    """Tray photo (any size) -> straightened TrayView, always 1120 x 640 px, or None.

    Pipelines 2 and 3 (SP3, SP4, SP6). Uses ArUco ids 0-3 on the tray sheet corners and warps
    the tray to 7 day columns x 4 slot rows of 160 px. cells[i] and cell_boxes[i] are
    compartment i (cell = day * 4 + slot; cell_boxes[i] == cell_box(i)).
    None = not all 4 markers seen: lid open, a marker covered, or a bad photo (FR-C-15).
    """
    # TODO(Joshua): replace the line below with your real code.
    return fake_results.rectify(img)
