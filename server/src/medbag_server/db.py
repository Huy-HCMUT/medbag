"""SQLite storage (FR-S-05): one file, photos in a folder. Complex objects are stored as JSON
from the medbag_common models, so what goes in is exactly what comes out.

Tables
  settings    one row: dose times and delays (FR-F-11)
  schedules   approved schedules; only the newest active one is used (FR-P-07)
  ref_photos  reference photos of each medicine, saved after the family confirms (FR-P-10)
  doses       one row per dose: its compartment, due time, state and the before photo (FR-C-02, C-04)
  checks      every check: fill, pre-dose, dose and lid checks, with the result (FR-C-12)
  log         the dose log that alert_rules and the voice read (FR-C-10)
  alerts      alerts shown on the family app until handled (FR-F-05)
  state       small values, e.g. the simulator's current time
"""

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import DB_PATH, PHOTO_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings   (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS schedules  (id INTEGER PRIMARY KEY, data TEXT NOT NULL, approved_by TEXT NOT NULL,
                                       approved_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS ref_photos (id INTEGER PRIMARY KEY, medicine_id TEXT NOT NULL, path TEXT NOT NULL,
                                       fingerprint TEXT NOT NULL, saved_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS doses      (dose_id TEXT PRIMARY KEY, cell INTEGER NOT NULL, slot TEXT NOT NULL,
                                       due_at TEXT NOT NULL, state TEXT NOT NULL,
                                       before_photo TEXT, before_mm_per_px REAL, done_at TEXT);
CREATE TABLE IF NOT EXISTS checks     (id INTEGER PRIMARY KEY, dose_id TEXT, at TEXT NOT NULL,
                                       kind TEXT NOT NULL, result TEXT NOT NULL,
                                       photo TEXT, mm_per_px REAL, answer TEXT);
CREATE TABLE IF NOT EXISTS log        (id INTEGER PRIMARY KEY, at TEXT NOT NULL, dose_id TEXT NOT NULL,
                                       kind TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS alerts     (id INTEGER PRIMARY KEY, dose_id TEXT, reason TEXT NOT NULL,
                                       message TEXT NOT NULL, check_id INTEGER,
                                       created_at TEXT NOT NULL, handled_at TEXT);
CREATE TABLE IF NOT EXISTS state      (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")  # the family app reads while the simulator writes
    return con


@contextmanager
def session() -> Iterator[sqlite3.Connection]:
    """One connection per request: saves everything at the end, or nothing if an error happens."""
    con = connect()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init() -> None:
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    with session() as con:
        con.executescript(SCHEMA)
