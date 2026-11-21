"""preprocess_label (Joshua). Write your code in this function; keep the name and the parameters.

What it takes in and gives back: packages/medbag_common/README.md (the function table)
and packages/medbag_common/examples/preprocess_label.json (a real example).
Test:  uv run pytest packages/prep
"""

from __future__ import annotations

import numpy as np

from medbag_common import fake_results
from medbag_common.types import PreparedLabel


def preprocess_label(img: np.ndarray) -> PreparedLabel:
    """Label photo -> cropped, straightened label with the patient name blurred.

    Pipeline 1 (SP1). `image` is the colour label for Gemini; `binary` is the same label in
    black and white with the noise removed, for Tesseract (one channel, 0 or 255).
    If no label is found or it is blurred, return found/sharp = False (both images may be
    the input photo); the server then asks for a new photo.
    """
    # TODO(Joshua): replace the line below with your real code.
    return fake_results.preprocess_label(img)
