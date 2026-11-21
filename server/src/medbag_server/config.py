"""Server settings, read from .env (never commit .env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]  # the repo folder
load_dotenv(ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DB_PATH = ROOT / os.getenv("MEDBAG_DB", "data/medbag.db")
PHOTO_DIR = ROOT / os.getenv("MEDBAG_PHOTOS", "data/photos")
