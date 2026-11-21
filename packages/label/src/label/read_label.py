"""read_label (Sam). Write your code in this function; keep the name and the parameters.

What it takes in and gives back: packages/medbag_common/README.md (the function table)
and packages/medbag_common/examples/read_label.json (a real example).
Test:  uv run pytest packages/label
"""

from __future__ import annotations

from typing import Any

from medbag_common import fake_results
from medbag_common.types import LabelResult, PreparedLabel


def read_label(label: PreparedLabel, gemini: Any) -> LabelResult:
    """Prepared label -> LabelResult (Gemini first, Tesseract chi_tra as fallback).

    Pipeline 1 (SP1). Only called when label.found and label.sharp. Gemini reads
    label.image; Tesseract reads label.binary. `gemini` is the client the server made with
    its API key; it may be None when there is no internet. Use Tesseract when it is None,
    fails or returns something that is not the agreed JSON, and set engine = "tesseract"
    plus a fallback_used flag. engine is always "gemini" or "tesseract" here ("none" is
    set by the server). Fill missing slots from the frequency, never overwrite slots read
    from ticks or icons.
    """
    # TODO(Sam): replace the line below with your real code.
    return fake_results.read_label(label, gemini)
