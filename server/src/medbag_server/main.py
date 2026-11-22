"""FastAPI app. Run:  uv run uvicorn medbag_server.main:app --reload --host 0.0.0.0 --port 8000

Simulator: http://localhost:8000/sim     Family app: http://<laptop IP>:8000/family
API docs (try every endpoint in the browser): http://localhost:8000/docs

Endpoints follow the table in the Functional Requirements doc. Each one reads the request,
calls one function in pipelines.py, saves to the database (store.py) and replies.
The simulator owns the clock: it sends its time with every request, and the server keeps the
latest one, so "today" on the family app is the simulator's day.
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from medbag_common.types import (
    Answer,
    CellState,
    CheckResult,
    DoseResult,
    DoseState,
    LabelResult,
    Match,
    Schedule,
    Settings,
    TrayResult,
    make_schedule,
)

from . import db, pipelines, store
from .api_models import (
    AnswerIn,
    ApproveIn,
    AskIn,
    CheckOut,
    ClearHoldIn,
    ConfirmFillIn,
    DoseStatus,
    FillOut,
    PreDoseOut,
    RefillIn,
    TickIn,
    TickOut,
    TodayOut,
    bad,
    check_medicines,
    check_settings,
)
from .config import DB_PATH, GEMINI_API_KEY, PHOTO_DIR
from .doses import current_dose, dose_from_id, doses_of_day
from .images import BadPhoto, load_photo
from .pipelines import Models

WEB = Path(__file__).resolve().parents[2] / "web"
ASK_TIMEOUT_S = 5  # FR-V-02: no answer in 5 s -> scripted fallback
TAKEN = {DoseState.removed, DoseState.taken_late}
requests_log = logging.getLogger("medbag.requests")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    handler = logging.FileHandler(DB_PATH.parent / "requests.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    requests_log.addHandler(handler)
    requests_log.setLevel(logging.INFO)
    # Load YOLO26n, DINOv2 and the Gemini client here, once; pipelines.py passes them on.
    app.state.models = Models(yolo=None, dino=None, gemini=None)  # e.g. gemini=genai.Client(api_key=GEMINI_API_KEY)
    yield
    requests_log.removeHandler(handler)
    handler.close()


app = FastAPI(title="The Talking Medicine Bag", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """FR-S-06: every request with its time, status and how long it took."""
    start = time.perf_counter()
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        ms = (time.perf_counter() - start) * 1000
        requests_log.info("%s %s %s %.0f ms", request.method, request.url.path, response.status_code, ms)
    return response


@app.exception_handler(BadPhoto)
def bad_photo(request: Request, exc: BadPhoto):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# ------------------------------------------------------------------ helpers


def models() -> Models:
    return app.state.models


async def read_photo(photo: Optional[UploadFile], kind: Literal["label", "tray"]):
    if photo is None:
        raise bad("Send a photo.")
    return load_photo(await photo.read(), kind)


def now(con) -> datetime:
    """The simulator's time if it has sent one, else the laptop's time."""
    return store.get_sim_time(con) or datetime.now().replace(microsecond=0)


def need_schedule(con) -> Schedule:
    schedule = store.get_schedule(con)
    if schedule is None:
        raise HTTPException(status_code=409, detail="No approved schedule yet. Approve one in the family app first.")
    return schedule


def url(name: Optional[str]) -> Optional[str]:
    return f"/photos/{name}" if name else None


def stamp(t: datetime) -> str:
    return t.strftime("%Y%m%d_%H%M%S")


def mark_taken(con, dose_id: str, at: datetime) -> DoseState:
    """Removed on time, or taken late if the family was already alerted (FR-C-10)."""
    late = any(e.kind == "family_alert" and e.dose_id == dose_id and e.detail.get("reason") == "late"
               for e in store.get_log(con))
    state = DoseState.taken_late if late else DoseState.removed
    store.set_dose_state(con, dose_id, state, at)
    return state


def save_unsure_pills(con, matches: list[Match], image_name: Optional[str], at: datetime) -> int:
    """A pill the family confirmed becomes a reference photo (FR-F-06, FR-P-10)."""
    if not image_name:
        return 0
    image = store.load_image(image_name)
    saved = 0
    for m in matches:
        if m.certainty.value == "unsure" and m.medicine_id:
            store.add_ref(con, m.medicine_id, store.crop(image, m.pill.box), m.fingerprint, at)
            saved += 1
    return saved


# ------------------------------------------------------------------ server


@app.get("/api/health")
def health():
    return {"ok": True, "gemini_key": bool(GEMINI_API_KEY)}


# ------------------------------------------------------------------ settings (FR-F-11)


@app.get("/api/settings")
def get_settings() -> Settings:
    with db.session() as con:
        return store.get_settings(con)


@app.put("/api/settings")
def put_settings(settings: Settings) -> Settings:
    check_settings(settings)
    with db.session() as con:
        store.put_settings(con, settings)
    return settings


# ------------------------------------------------------------------ Function 1: prepare


@app.post("/api/ocr")
async def ocr(photo: UploadFile = File(...)) -> LabelResult:
    """FR-P-01..P-04: label photo -> medicines read from it, with flags for the family to check."""
    img = await read_photo(photo, "label")
    return pipelines.label_check(img, models())


@app.post("/api/schedule/approve")
def approve(body: ApproveIn) -> Schedule:
    """FR-P-05..P-08: the family approves the corrected medicines; nothing is reminded before this."""
    check_medicines(body.medicines, body.approved_by)
    with db.session() as con:
        schedule = make_schedule(body.medicines, body.approved_by.strip(), now(con))
        store.save_schedule(con, schedule)
    return schedule


@app.get("/api/schedule")
def get_schedule() -> Schedule:
    with db.session() as con:
        return need_schedule(con)


@app.post("/api/tray")
async def tray(mode: Literal["fill", "pre_dose"] = Form(...), sim_time: datetime = Form(...),
               photo: Optional[UploadFile] = File(None)) -> FillOut | PreDoseOut:
    """One full-tray photo, lid closed.

    mode=fill      the fill check after filling (FR-P-12); the family confirms with /api/tray/confirm.
    mode=pre_dose  at a dose time, before reminding (FR-C-02). Without a photo (click mode) the dose
                   simply opens. A wrong, extra or unsure pill, or an empty compartment, holds the dose.
    """
    img = await read_photo(photo, "tray") if photo is not None else None
    with db.session() as con:
        store.set_sim_time(con, sim_time)
        schedule = need_schedule(con)
        refs = store.get_refs(con)
        if mode == "fill":
            if img is None:
                raise bad("The fill check needs a photo of the whole tray.")
            out = pipelines.fill_check(img, schedule, refs or None, models())
            if out is None:
                return FillOut(check_id=None, result=None, view_url=None, say="cannot_check")
            name = store.save_view(out.view, f"fill_{stamp(sim_time)}.png")
            store.set_last_view(con, name, out.view.mm_per_px)
            check_id = store.add_check(con, None, sim_time, "fill", out.result, name, out.view.mm_per_px)
            return FillOut(check_id=check_id, result=out.result, view_url=url(name), say="fill_checked")
        return pre_dose(con, img, sim_time, schedule, refs)


def pre_dose(con, img, sim_time: datetime, schedule: Schedule, refs) -> PreDoseOut:
    settings = store.get_settings(con)
    dose = current_dose(sim_time, settings)
    if dose is None:
        raise HTTPException(status_code=409, detail="No dose time has started yet.")
    if not schedule.cells.get(dose.cell):
        raise HTTPException(status_code=409, detail=f"No medicine is due at {dose.slot.value}.")
    row = store.get_dose(con, dose.dose_id)
    if row and row["state"] != DoseState.upcoming.value:  # sent twice: reply with what already happened
        return PreDoseOut(dose=dose, state=DoseState(row["state"]), result=None,
                          view_url=url(row["before_photo"]), say="already_started")
    if img is None:  # click mode (FR-B-08)
        store.start_dose(con, dose.dose_id, dose.cell, dose.slot.value, dose.due_at, DoseState.open, None, None)
        store.add_log(con, sim_time, dose.dose_id, "reminder", {"mode": "click"})
        return PreDoseOut(dose=dose, state=DoseState.open, result=None, view_url=None, say="reminder")

    out = pipelines.pre_dose_check(img, dose, schedule, refs, models())
    name = store.save_view(out.view, f"before_{dose.dose_id}.png") if out.view else None
    mm = out.view.mm_per_px if out.view else None
    if name:
        store.set_last_view(con, name, mm)
    check_id = store.add_check(con, dose.dose_id, sim_time, "pre_dose",
                               out.result or {"result": "cannot_check"}, name, mm)
    if out.hold:
        cell = out.result.cells[0]
        store.start_dose(con, dose.dose_id, dose.cell, dose.slot.value, dose.due_at, DoseState.on_hold, name, mm)
        store.add_log(con, sim_time, dose.dose_id, "on_hold", {"state": cell.state.value, "check_id": check_id})
        alert_id = store.add_alert(con, sim_time, dose.dose_id, "pre_dose_problem",
                                   cell.note or f"Pre-dose check: {cell.state.value} pill in today's {dose.slot.value} compartment.",
                                   check_id)
        return PreDoseOut(dose=dose, state=DoseState.on_hold, result=out.result, view_url=url(name),
                          say="please_wait", alert_id=alert_id)
    store.start_dose(con, dose.dose_id, dose.cell, dose.slot.value, dose.due_at, DoseState.open, name, mm)
    missing = out.result is not None and out.result.cells[0].state == CellState.missing
    store.add_log(con, sim_time, dose.dose_id, "reminder", {"check_id": check_id, "missing_pill": missing})
    return PreDoseOut(dose=dose, state=DoseState.open, result=out.result, view_url=url(name),
                      say="reminder_missing_pill" if missing else "reminder")


@app.post("/api/tray/confirm")
def confirm_fill(body: ConfirmFillIn):
    """FR-P-10: the family confirmed the fill-check grid -> save the reference photos."""
    with db.session() as con:
        row = store.latest_check(con, "fill")
        if row is None or row["answer"] is not None:
            raise HTTPException(status_code=409, detail="There is no fill check waiting for confirmation.")
        at = now(con)
        result = TrayResult.model_validate_json(row["result"])
        image = store.load_image(row["photo"])
        saved = [store.add_ref(con, r.medicine_id, store.crop(image, r.pill.box), r.fingerprint, at)
                 for r in result.refs_to_save]
        store.answer_check(con, row["id"], {"confirmed_by": body.by, "at": at.isoformat()})
    return {"saved": [r.model_dump() | {"url": url(r.path)} for r in saved]}


# ------------------------------------------------------------------ Function 2: remind and check


@app.post("/api/check")
async def check(sim_time: datetime = Form(...), photo: UploadFile = File(...)) -> CheckOut:
    """The lid closed: compare the after photo with the before photo (FR-C-04, C-08, C-13)."""
    img = await read_photo(photo, "tray")
    with db.session() as con:
        store.set_sim_time(con, sim_time)
        schedule = need_schedule(con)
        settings = store.get_settings(con)
        dose = current_dose(sim_time, settings)
        row = store.get_dose(con, dose.dose_id) if dose else None
        if row is not None and row["state"] == DoseState.open.value:
            return dose_after(con, img, sim_time, dose, row, schedule)
        return lid_after(con, img, sim_time)


def dose_after(con, img, sim_time, dose, row, schedule) -> CheckOut:
    before = store.load_view(row["before_photo"], row["before_mm_per_px"]) if row["before_photo"] else None
    out = pipelines.dose_check(before, img, dose, schedule, store.get_refs(con), models())
    result: CheckResult = out.result
    name = store.save_view(out.view, f"after_{dose.dose_id}_{stamp(sim_time)}.png") if out.view else None
    if name:
        store.set_last_view(con, name, out.view.mm_per_px)
    check_id = store.add_check(con, dose.dose_id, sim_time, "dose", result, name, out.view.mm_per_px if out.view else None)

    previous = [e for e in store.get_log(con) if e.dose_id == dose.dose_id and e.kind == "check"]
    store.add_log(con, sim_time, dose.dose_id, "check", {"result": result.result.value, "check_id": check_id})
    wrong = {DoseResult.wrong_pill.value, DoseResult.extra_pill.value}
    if previous and previous[-1].detail.get("result") in wrong and result.result.value not in wrong:
        store.add_log(con, sim_time, dose.dose_id, "put_back", {"check_id": check_id})  # FR-C-09

    alert_ids = []
    if result.result == DoseResult.correct:
        mark_taken(con, dose.dose_id, sim_time)
    elif result.result == DoseResult.unsure:  # FR-F-06: the family confirms or rejects
        alert_ids.append(store.add_alert(con, sim_time, dose.dose_id, "unsure_pill",
                                         "The camera is not sure about a pill. Please look at the photo.", check_id))
    if result.other_changed_cells:  # FR-C-13
        cells = ", ".join(str(c) for c in result.other_changed_cells)
        alert_ids.append(store.add_alert(con, sim_time, dose.dose_id, "other_compartment",
                                         f"Another compartment changed: {cells}.", check_id))
    return CheckOut(check_id=check_id, kind="dose", result=result, changed_cells=result.other_changed_cells,
                    view_url=url(name), say=result.message_key, alert_ids=alert_ids)


def lid_after(con, img, sim_time) -> CheckOut:
    """The lid closed when no dose was open (SP6 "Dose open? No"), compared with the newest tray photo.
    That photo is then replaced, so the same change never alerts twice (FR-C-13)."""
    out = pipelines.lid_check(store.get_last_view(con), img)
    name = store.save_view(out.view, f"lid_{stamp(sim_time)}.png") if out.view else None
    if name:
        store.set_last_view(con, name, out.view.mm_per_px)
    if not out.changed:
        return CheckOut(check_id=None, kind="lid", result=None, view_url=url(name), say=None)
    check_id = store.add_check(con, None, sim_time, "lid", {"changed_cells": out.changed}, name,
                               out.view.mm_per_px)
    store.add_log(con, sim_time, "", "check", {"kind": "lid", "changed_cells": out.changed, "check_id": check_id})
    alert_ids = [store.add_alert(
        con, sim_time, None, "lid_changed",
        f"The box was opened when no dose was due. Changed compartments: {', '.join(map(str, out.changed))}.", check_id)]
    return CheckOut(check_id=check_id, kind="lid", result=None, changed_cells=out.changed,
                    view_url=url(name), say="not_time_yet", alert_ids=alert_ids)


@app.post("/api/events")
def tick(body: TickIn) -> TickOut:
    """The simulator's clock: run the reminder and alert rules for this moment (FR-C-09, C-10)."""
    with db.session() as con:
        store.set_sim_time(con, body.sim_time)
        settings = store.get_settings(con)
        actions = pipelines.alerts(store.get_log(con, body.sim_time - timedelta(days=2)), body.sim_time, settings)
        say = []
        for a in actions:
            row = store.get_dose(con, a.dose_id)
            if a.kind == "second_reminder":
                store.add_log(con, body.sim_time, a.dose_id, "second_reminder", {"reason": a.reason})
                say.append(a.message_key)
            elif a.kind == "family_alert":
                store.add_log(con, body.sim_time, a.dose_id, "family_alert", {"reason": a.reason})
                store.add_alert(con, body.sim_time, a.dose_id, a.reason, ALERT_TEXT.get(a.reason, a.reason))
            elif a.kind == "mark_missed" and (row is None or DoseState(row["state"]) not in TAKEN):
                d = dose_from_id(a.dose_id, settings)
                store.start_dose(con, d.dose_id, d.cell, d.slot.value, d.due_at, DoseState.missed, None, None)
            elif a.kind == "mark_taken_late" and row is not None:
                store.set_dose_state(con, a.dose_id, DoseState.taken_late, body.sim_time)
    return TickOut(sim_time=body.sim_time, actions=actions, say=say)


ALERT_TEXT = {
    "late": "The dose has not been taken yet.",
    "wrong_pill_not_put_back": "A pill that is not for now was taken out and not put back.",
    "other_compartment": "A pill was taken from another compartment.",
    "pre_dose_problem": "The pre-dose check found a problem.",
    "missed": "A dose was missed.",
}


@app.get("/api/events")
def today() -> TodayOut:
    """FR-F-04, F-05: the family app polls this every 2-3 s."""
    with db.session() as con:
        sim_time = store.get_sim_time(con)
        schedule = store.get_schedule(con)
        settings = store.get_settings(con)
        day = (sim_time or datetime.now()).date()
        names = {m.id: m for m in schedule.medicines} if schedule else {}
        doses = []
        for d in doses_of_day(day, settings):
            expected = schedule.cells.get(d.cell, []) if schedule else []
            if not expected:
                continue
            row = store.get_dose(con, d.dose_id)
            doses.append(DoseStatus(
                dose_id=d.dose_id, slot=d.slot, cell=d.cell, due_at=d.due_at,
                state=DoseState(row["state"]) if row else DoseState.upcoming,
                done_at=row["done_at"] if row else None,
                medicines=[{"medicine_id": e.medicine_id, "name": names[e.medicine_id].name,
                            "purpose": names[e.medicine_id].purpose, "count": e.count} for e in expected]))
        waiting = []
        for r in store.waiting_checks(con):
            result = CheckResult.model_validate_json(r["result"])
            unsure = [m.model_dump(mode="json") for m in result.taken + result.left if m.certainty.value == "unsure"]
            waiting.append({"check_id": r["id"], "dose_id": r["dose_id"], "at": r["at"],
                            "photo_url": url(r["photo"]), "unsure": unsure})
        log = [e.model_dump(mode="json") for e in store.get_log(con, datetime.combine(day, datetime.min.time()))][-30:]
        return TodayOut(sim_time=sim_time, schedule_approved=schedule is not None, doses=doses,
                        alerts=store.open_alerts(con), waiting_checks=waiting, log=log)


@app.post("/api/alerts/{alert_id}/handled")
def alert_handled(alert_id: int):
    with db.session() as con:
        if not store.handle_alert(con, alert_id, now(con)):
            raise HTTPException(status_code=404, detail="No open alert with this id.")
    return {"ok": True}


@app.post("/api/doses/{dose_id}/clear")
def clear_hold(dose_id: str, body: ClearHoldIn):
    """FR-C-02: the family releases a held dose.

    camera_wrong  the camera was wrong: the compartment opens and the reminder plays.
    tray_fixed    the tray was fixed: the dose goes back to upcoming, so the simulator sends a new
                  pre-dose photo and the check runs again.
    """
    with db.session() as con:
        row = store.get_dose(con, dose_id)
        if row is None or row["state"] != DoseState.on_hold.value:
            raise HTTPException(status_code=409, detail="This dose is not on hold.")
        at = now(con)
        store.add_log(con, at, dose_id, "hold_cleared", {"reason": body.reason, "by": body.by})
        store.handle_alerts_of_dose(con, dose_id, "pre_dose_problem", at)
        if body.reason == "camera_wrong":
            store.set_dose_state(con, dose_id, DoseState.open)
            store.add_log(con, at, dose_id, "reminder", {"after_hold": True})
            return {"state": DoseState.open, "say": "reminder"}
        store.set_dose_state(con, dose_id, DoseState.upcoming)
        return {"state": DoseState.upcoming, "say": None}


@app.post("/api/checks/{check_id}/answer")
def answer_check(check_id: int, body: AnswerIn):
    """FR-F-06: the family confirms or rejects an unsure pill.

    Confirm: the pill photo becomes a reference photo and the dose counts as taken.
    Reject: it counts as a wrong pill, so the box asks her to put it back (FR-C-09).
    """
    with db.session() as con:
        row = store.get_check(con, check_id)
        if row is None or row["kind"] != "dose":
            raise HTTPException(status_code=404, detail="No dose check with this id.")
        result = CheckResult.model_validate_json(row["result"])
        if result.result != DoseResult.unsure or row["answer"] is not None:
            raise HTTPException(status_code=409, detail="This check is not waiting for an answer.")
        at = now(con)
        dose_id = row["dose_id"]
        dose = store.get_dose(con, dose_id)
        store.answer_check(con, check_id, {"confirm": body.confirm, "by": body.by, "at": at.isoformat()})
        store.handle_alerts_of_dose(con, dose_id, "unsure_pill", at)
        if body.confirm:
            saved = save_unsure_pills(con, result.taken, dose["before_photo"] if dose else None, at)
            saved += save_unsure_pills(con, result.left, row["photo"], at)
            state = mark_taken(con, dose_id, at)
            store.add_log(con, at, dose_id, "check", {"result": "correct", "check_id": check_id, "by": body.by})
            return {"state": state, "refs_saved": saved, "say": "well_done"}
        store.add_log(con, at, dose_id, "check", {"result": "wrong_pill", "check_id": check_id, "by": body.by})
        return {"state": DoseState(dose["state"]) if dose else None, "refs_saved": 0, "say": "put_back"}


@app.post("/api/refill")
def refill(body: RefillIn):
    """FR-P-15 (Should): a refill keeps the schedule and goes to guided filling;
    a new prescription stops the schedule and starts again from a label photo."""
    with db.session() as con:
        need_schedule(con)
        if body.kind == "new_prescription":
            store.stop_schedule(con)
            return {"next": "label_photo"}
        return {"next": "guided_filling"}


@app.post("/api/ask")
def ask(body: AskIn) -> Answer:
    """FR-V-02, V-04: a spoken question, answered only from her schedule and log."""
    with db.session() as con:
        schedule = need_schedule(con)
        log = store.get_log(con, now(con) - timedelta(days=7))
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = pool.submit(pipelines.ask, body.question, schedule, log, body.language, models())
    try:
        return future.result(timeout=ASK_TIMEOUT_S)
    except concurrent.futures.TimeoutError:
        text = "我現在無法回答，請問您的家人。" if body.language == "zh-TW" else "I cannot answer now, please ask your family."
        return Answer(text=text, language=body.language, fallback=True)
    finally:
        pool.shutdown(wait=False)


# ------------------------------------------------------------------ web pages and photos

app.mount("/photos", StaticFiles(directory=PHOTO_DIR, check_dir=False), name="photos")
app.mount("/sim", StaticFiles(directory=WEB / "sim", html=True), name="sim")
app.mount("/family", StaticFiles(directory=WEB / "family", html=True), name="family")
