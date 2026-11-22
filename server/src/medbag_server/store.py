"""Read and write everything the server keeps (tables in db.py, images in the photo folder).

Every function takes the open connection `con` from db.session(), so one request is saved
all together or not at all.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Optional

import numpy as np
from PIL import Image

from medbag_common.types import (
    Box,
    CheckResult,
    DoseState,
    Fingerprint,
    LogEntry,
    RefPhoto,
    Schedule,
    Settings,
    TrayResult,
    TrayView,
    cell_box,
)

from .config import PHOTO_DIR

# ------------------------------------------------------------------ settings and clock


def get_settings(con: sqlite3.Connection) -> Settings:
    row = con.execute("SELECT data FROM settings WHERE id = 1").fetchone()
    return Settings.model_validate_json(row["data"]) if row else Settings()


def put_settings(con: sqlite3.Connection, settings: Settings) -> None:
    con.execute("INSERT OR REPLACE INTO settings (id, data) VALUES (1, ?)", (settings.model_dump_json(),))


def get_sim_time(con: sqlite3.Connection) -> Optional[datetime]:
    row = con.execute("SELECT value FROM state WHERE key = 'sim_time'").fetchone()
    return datetime.fromisoformat(row["value"]) if row else None


def set_sim_time(con: sqlite3.Connection, t: datetime) -> None:
    con.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('sim_time', ?)", (t.isoformat(),))


# ------------------------------------------------------------------ schedule and reference photos


def get_schedule(con: sqlite3.Connection) -> Optional[Schedule]:
    row = con.execute("SELECT data FROM schedules WHERE active = 1 ORDER BY id DESC LIMIT 1").fetchone()
    return Schedule.model_validate_json(row["data"]) if row else None


def save_schedule(con: sqlite3.Connection, schedule: Schedule) -> None:
    """The new schedule replaces the old one (FR-F-08: the box keeps the old one until this moment)."""
    con.execute("UPDATE schedules SET active = 0")
    con.execute("INSERT INTO schedules (data, approved_by, approved_at) VALUES (?, ?, ?)",
                (schedule.model_dump_json(), schedule.approved_by, schedule.approved_at.isoformat()))


def stop_schedule(con: sqlite3.Connection) -> None:
    con.execute("UPDATE schedules SET active = 0")


def get_refs(con: sqlite3.Connection) -> list[RefPhoto]:
    rows = con.execute("SELECT medicine_id, path, fingerprint FROM ref_photos ORDER BY id").fetchall()
    return [RefPhoto(medicine_id=r["medicine_id"], path=r["path"],
                     fingerprint=Fingerprint.model_validate_json(r["fingerprint"])) for r in rows]


def add_ref(con: sqlite3.Connection, medicine_id: str, crop: np.ndarray, fp: Fingerprint, at: datetime) -> RefPhoto:
    cur = con.execute("INSERT INTO ref_photos (medicine_id, path, fingerprint, saved_at) VALUES (?, '', ?, ?)",
                      (medicine_id, fp.model_dump_json(), at.isoformat()))
    path = save_image(crop, f"ref_{cur.lastrowid}_{medicine_id}.png")
    con.execute("UPDATE ref_photos SET path = ? WHERE id = ?", (path, cur.lastrowid))
    return RefPhoto(medicine_id=medicine_id, path=path, fingerprint=fp)


# ------------------------------------------------------------------ images


def save_image(img: np.ndarray, name: str) -> str:
    """Save a BGR image as PNG in the photo folder; returns the name (served at /photos/<name>)."""
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.ascontiguousarray(img[:, :, ::-1])).save(PHOTO_DIR / name)
    return name


def load_image(name: str) -> np.ndarray:
    rgb = np.asarray(Image.open(PHOTO_DIR / name).convert("RGB"), dtype=np.uint8)
    return np.ascontiguousarray(rgb[:, :, ::-1])


def save_view(view: TrayView, name: str) -> str:
    return save_image(view.image, name)


def load_view(name: str, mm_per_px: float) -> TrayView:
    """Rebuild a saved straightened tray (always 1120 x 640) as a TrayView."""
    image = load_image(name)
    boxes = [cell_box(c) for c in range(28)]
    cells = [image[int(b.y):int(b.y + b.h), int(b.x):int(b.x + b.w)] for b in boxes]
    return TrayView(image=image, cells=cells, cell_boxes=boxes, mm_per_px=mm_per_px)


def crop(image: np.ndarray, box: Box, margin: int = 4) -> np.ndarray:
    h, w = image.shape[:2]
    x0, y0 = max(0, int(box.x) - margin), max(0, int(box.y) - margin)
    x1, y1 = min(w, int(box.x + box.w) + margin), min(h, int(box.y + box.h) + margin)
    return image[y0:y1, x0:x1]


# ------------------------------------------------------------------ doses


def get_dose(con: sqlite3.Connection, dose_id: str) -> Optional[sqlite3.Row]:
    return con.execute("SELECT * FROM doses WHERE dose_id = ?", (dose_id,)).fetchone()


def start_dose(con: sqlite3.Connection, dose_id: str, cell: int, slot: str, due_at: datetime,
               state: DoseState, before_photo: Optional[str], mm_per_px: Optional[float]) -> None:
    con.execute(
        """INSERT INTO doses (dose_id, cell, slot, due_at, state, before_photo, before_mm_per_px)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(dose_id) DO UPDATE SET state = excluded.state,
             before_photo = COALESCE(excluded.before_photo, doses.before_photo),
             before_mm_per_px = COALESCE(excluded.before_mm_per_px, doses.before_mm_per_px)""",
        (dose_id, cell, slot, due_at.isoformat(), state.value, before_photo, mm_per_px))


def set_dose_state(con: sqlite3.Connection, dose_id: str, state: DoseState, at: Optional[datetime] = None) -> None:
    con.execute("UPDATE doses SET state = ?, done_at = COALESCE(?, done_at) WHERE dose_id = ?",
                (state.value, at.isoformat() if at else None, dose_id))


def set_last_view(con: sqlite3.Connection, name: str, mm_per_px: float) -> None:
    """The newest straightened tray photo: what the tray looks like now."""
    con.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('last_view', ?)",
                (json.dumps({"name": name, "mm_per_px": mm_per_px}),))


def get_last_view(con: sqlite3.Connection) -> Optional[TrayView]:
    """Used when the lid closes with no dose open: compare with how the tray looked last time."""
    row = con.execute("SELECT value FROM state WHERE key = 'last_view'").fetchone()
    if row is None:
        return None
    v = json.loads(row["value"])
    return load_view(v["name"], v["mm_per_px"])


def doses_between(con: sqlite3.Connection, start: datetime, end: datetime) -> list[sqlite3.Row]:
    return con.execute("SELECT * FROM doses WHERE due_at >= ? AND due_at < ? ORDER BY due_at",
                       (start.isoformat(), end.isoformat())).fetchall()


# ------------------------------------------------------------------ checks


def add_check(con: sqlite3.Connection, dose_id: Optional[str], at: datetime, kind: str,
              result: CheckResult | TrayResult | dict, photo: Optional[str], mm_per_px: Optional[float]) -> int:
    data = result if isinstance(result, dict) else result.model_dump(mode="json")
    cur = con.execute("INSERT INTO checks (dose_id, at, kind, result, photo, mm_per_px) VALUES (?, ?, ?, ?, ?, ?)",
                      (dose_id, at.isoformat(), kind, json.dumps(data, ensure_ascii=False), photo, mm_per_px))
    return cur.lastrowid


def get_check(con: sqlite3.Connection, check_id: int) -> Optional[sqlite3.Row]:
    return con.execute("SELECT * FROM checks WHERE id = ?", (check_id,)).fetchone()


def latest_check(con: sqlite3.Connection, kind: str) -> Optional[sqlite3.Row]:
    return con.execute("SELECT * FROM checks WHERE kind = ? ORDER BY id DESC LIMIT 1", (kind,)).fetchone()


def answer_check(con: sqlite3.Connection, check_id: int, answer: dict) -> None:
    con.execute("UPDATE checks SET answer = ? WHERE id = ?", (json.dumps(answer, ensure_ascii=False), check_id))


def waiting_checks(con: sqlite3.Connection) -> list[sqlite3.Row]:
    """Dose checks with an unsure pill that the family has not answered yet (FR-F-06)."""
    return con.execute("""SELECT * FROM checks WHERE kind = 'dose' AND answer IS NULL
                          AND json_extract(result, '$.result') = 'unsure' ORDER BY id""").fetchall()


# ------------------------------------------------------------------ log and alerts


def add_log(con: sqlite3.Connection, at: datetime, dose_id: str, kind: str, detail: Optional[dict] = None) -> None:
    con.execute("INSERT INTO log (at, dose_id, kind, detail) VALUES (?, ?, ?, ?)",
                (at.isoformat(), dose_id, kind, json.dumps(detail or {}, ensure_ascii=False)))


def get_log(con: sqlite3.Connection, since: Optional[datetime] = None) -> list[LogEntry]:
    rows = con.execute("SELECT at, dose_id, kind, detail FROM log WHERE at >= ? ORDER BY at, id",
                       ((since or datetime.min).isoformat(),)).fetchall()
    return [LogEntry(at=datetime.fromisoformat(r["at"]), dose_id=r["dose_id"], kind=r["kind"],
                     detail=json.loads(r["detail"])) for r in rows]


def add_alert(con: sqlite3.Connection, at: datetime, dose_id: Optional[str], reason: str, message: str,
              check_id: Optional[int] = None) -> int:
    cur = con.execute("INSERT INTO alerts (dose_id, reason, message, check_id, created_at) VALUES (?, ?, ?, ?, ?)",
                      (dose_id, reason, message, check_id, at.isoformat()))
    return cur.lastrowid


def open_alerts(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute("SELECT * FROM alerts WHERE handled_at IS NULL ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def handle_alert(con: sqlite3.Connection, alert_id: int, at: datetime) -> bool:
    cur = con.execute("UPDATE alerts SET handled_at = ? WHERE id = ? AND handled_at IS NULL", (at.isoformat(), alert_id))
    return cur.rowcount == 1


def handle_alerts_of_dose(con: sqlite3.Connection, dose_id: str, reason: str, at: datetime) -> None:
    con.execute("UPDATE alerts SET handled_at = ? WHERE dose_id = ? AND reason = ? AND handled_at IS NULL",
                (at.isoformat(), dose_id, reason))
