"""fingerprint (Emily). Write your code in this function; keep the name and the parameters.

What it takes in and gives back: packages/medbag_common/README.md (the function table)
and packages/medbag_common/examples/fingerprint.json (a real example).
Test:  uv run pytest packages/check
"""

from __future__ import annotations

from typing import Any

from medbag_common import fake_results
from medbag_common.types import Fingerprint, Pill, TrayView


def fingerprint(view: TrayView, pill: Pill, dino: Any = None) -> Fingerprint:
    """One pill -> colour, size in mm and shape (optionally a DINOv2 embedding).

    Used inside identify and match_fill, which put it into Match.fingerprint and
    RefToSave.fingerprint; the server does not call it.
    """
    # TODO(Emily): replace the line below with your real code.
    return fake_results.fingerprint(view, pill, dino)
