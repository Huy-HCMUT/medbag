"""images.load_photo: any phone photo -> upright BGR uint8, shrunk to the agreed size."""

import io

import numpy as np
import pytest
from PIL import Image

from medbag_server.images import BadPhoto, load_photo


def jpeg(w: int, h: int, orientation: int | None = None, colour=(255, 0, 0)) -> bytes:
    img = Image.new("RGB", (w, h), colour)
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif.tobytes())
    return buf.getvalue()


def test_sideways_phone_photo_is_turned_upright():
    # stored 4000 x 3000 with "rotate 90" (orientation 6), as many phones do
    out = load_photo(jpeg(4000, 3000, orientation=6), "tray")
    assert out.shape == (1600, 1200, 3)  # upright (portrait) and longest side 1600


def test_label_keeps_more_pixels_than_tray():
    assert max(load_photo(jpeg(4032, 3024), "label").shape[:2]) == 2000
    assert max(load_photo(jpeg(4032, 3024), "tray").shape[:2]) == 1600


def test_small_photo_is_not_enlarged():
    assert load_photo(jpeg(1280, 960), "label").shape == (960, 1280, 3)


def test_colour_order_is_bgr_uint8():
    out = load_photo(jpeg(800, 600, colour=(255, 0, 0)), "tray")  # pure red
    assert out.dtype == np.uint8
    b, g, r = out[300, 400]
    assert r > 200 and b < 50


def test_not_a_photo():
    with pytest.raises(BadPhoto):
        load_photo(b"not an image", "label")


def test_too_small():
    with pytest.raises(BadPhoto):
        load_photo(jpeg(320, 240), "tray")
