"""SQLite storage (FR-S-05): one file, photos in a folder. Complex objects are JSON from medbag_common models."""

import sqlite3

from .config import DB_PATH, PHOTO_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings   (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT);
CREATE TABLE IF NOT EXISTS schedules  (id INTEGER PRIMARY KEY, data TEXT, approved_by TEXT,
                                       approved_at TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS ref_photos (id INTEGER PRIMARY KEY, medicine_id TEXT, path TEXT,
                                       fingerprint TEXT);
CREATE TABLE IF NOT EXISTS doses      (dose_id TEXT PRIMARY KEY, cell INTEGER, slot TEXT,
                                       due_at TEXT, state TEXT, before_photo TEXT);
CREATE TABLE IF NOT EXISTS checks     (id INTEGER PRIMARY KEY, dose_id TEXT, at TEXT, kind TEXT,
                                       result TEXT, after_photo TEXT);
CREATE TABLE IF NOT EXISTS log        (id INTEGER PRIMARY KEY, at TEXT, dose_id TEXT, kind TEXT,
                                       detail TEXT);
CREATE TABLE IF NOT EXISTS alerts     (id INTEGER PRIMARY KEY, dose_id TEXT, reason TEXT,
                                       created_at TEXT, handled_at TEXT);
"""


def connect() -> sqlite3.Connection:
    """One connection per request (FastAPI runs requests on several threads)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")  # the family app reads while the simulator writes
    return con


def init() -> None:
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as con:
        con.executescript(SCHEMA)
