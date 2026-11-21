"""Server settings, read from .env (never commit .env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]  # the repo folder
load_dotenv(ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DB_PATH = ROOT / os.getenv("MEDBAG_DB", "data/medbag.db")
PHOTO_DIR = ROOT / os.getenv("MEDBAG_PHOTOS", "data/photos")

# Set a function to True when its owner's real code passes the agreement test; False = fake result.
USE_REAL = {
    "preprocess_label": False, "rectify": False, "changed_cells": False,   # Joshua
    "read_label": False, "check_fields": False,                            # Sam
    "detect_pills": False, "answer": False,                                # Alex (pills, voice)
    "fingerprint": False, "identify": False, "match_fill": False,          # Emily
    "check_tray": False, "check_dose": False, "alert_rules": False,
}
