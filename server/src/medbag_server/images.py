"""Turn an uploaded phone photo into the image every function expects (numpy, BGR, uint8).

Phones send photos of different sizes, and many save them sideways with an EXIF "rotate" tag.
Every endpoint calls load_photo first, so no one else has to think about it:
  1. Turn the photo upright (EXIF orientation), then drop the EXIF data (location, phone model).
  2. Convert to 3-channel BGR uint8, the order cv2.imread gives.
  3. Shrink so the longest side is at most 2000 px (labels, small print) or 1600 px (trays).
     Smaller photos are left as they are; nothing is ever enlarged.
After rectify the tray is always 1120 x 640 px, so the pill functions see one size anyway.
"""

from __future__ import annotations

import io
from typing import Literal

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_SIDE = {"label": 2000, "tray": 1600}
MIN_SIDE = 480  # smaller than this cannot be read: ask for a new photo


class BadPhoto(ValueError):
    """The upload is not a photo we can use. The endpoint replies 400 with this message."""


def load_photo(data: bytes, kind: Literal["label", "tray"]) -> np.ndarray:
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)  # upright, whatever way the phone was held
    except (UnidentifiedImageError, OSError) as e:
        raise BadPhoto("This file is not a photo. Please send a JPEG or PNG.") from e
    img = img.convert("RGB")
    if min(img.size) < MIN_SIDE:
        raise BadPhoto("The photo is too small. Please take it again closer.")
    img.thumbnail((MAX_SIDE[kind], MAX_SIDE[kind]), Image.Resampling.LANCZOS)  # keeps the shape
    rgb = np.asarray(img, dtype=np.uint8)
    return np.ascontiguousarray(rgb[:, :, ::-1])  # RGB -> BGR
