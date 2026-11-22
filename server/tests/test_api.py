"""The endpoints, end to end, with everyone's fake results (FR table "Server and hosting")."""

import io
import shutil
import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from medbag_common import types as T
from medbag_server import main, pipelines
from medbag_server.config import DB_PATH, PHOTO_DIR

MON = "2026-11-23"  # a Monday
NOON_DOSE = f"{MON}-noon"
MEDICINE = {"id": "m1", "name": "Test tablet 5mg", "dose_per_time": 1, "frequency_per_day": 1,
            "slots": ["noon"], "purpose": "blood pressure"}


def jpeg(w=1200, h=900) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (120, 120, 120)).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def api():
    for p in (DB_PATH, DB_PATH.with_name(DB_PATH.name + "-wal"), DB_PATH.with_name(DB_PATH.name + "-shm")):
        p.unlink(missing_ok=True)
    shutil.rmtree(PHOTO_DIR, ignore_errors=True)
    with TestClient(main.app) as client:
        yield client


def approve(api):
    r = api.post("/api/schedule/approve", json={"medicines": [MEDICINE], "approved_by": "Daughter"})
    assert r.status_code == 200, r.text
    return r.json()


def tray(api, mode, at, photo=True):
    files = {"photo": ("tray.jpg", jpeg(), "image/jpeg")} if photo else None
    return api.post("/api/tray", data={"mode": mode, "sim_time": f"{MON}T{at}"}, files=files)


def close_lid(api, at):
    return api.post("/api/check", data={"sim_time": f"{MON}T{at}"}, files={"photo": ("t.jpg", jpeg(), "image/jpeg")})


def dose_state(api, dose_id=NOON_DOSE):
    return next(d["state"] for d in api.get("/api/events").json()["doses"] if d["dose_id"] == dose_id)


# ------------------------------------------------------------------ settings and schedule


def test_settings_are_checked_and_kept(api):
    assert api.get("/api/settings").json()["dose_times"]["noon"] == "12:30"
    s = api.get("/api/settings").json()
    assert api.put("/api/settings", json=s | {"dose_times": s["dose_times"] | {"noon": "07:00"}}).status_code == 400
    assert api.put("/api/settings", json=s | {"dose_times": s["dose_times"] | {"noon": "12h"}}).status_code == 400
    assert api.put("/api/settings", json=s | {"second_reminder_min": -1}).status_code == 400
    assert api.put("/api/settings", json=s | {"family_alert_min": 10}).status_code == 400  # before the 2nd reminder
    ok = api.put("/api/settings", json=s | {"dose_times": s["dose_times"] | {"noon": "13:00"}})
    assert ok.status_code == 200 and api.get("/api/settings").json()["dose_times"]["noon"] == "13:00"


def test_nothing_runs_before_approval(api):
    assert api.get("/api/schedule").status_code == 409
    assert tray(api, "pre_dose", "12:31").status_code == 409


def test_label_photo_is_read(api):
    r = api.post("/api/ocr", files={"photo": ("label.jpg", jpeg(), "image/jpeg")})
    assert r.status_code == 200 and r.json()["medicines"][0]["id"] == "m1"


def test_bad_photo_gets_a_clear_message(api):
    r = api.post("/api/ocr", files={"photo": ("label.jpg", b"not a photo", "image/jpeg")})
    assert r.status_code == 400 and "photo" in r.json()["detail"]


def test_approval_is_checked(api):
    bad = api.post("/api/schedule/approve", json={"medicines": [MEDICINE | {"slots": []}], "approved_by": "D"})
    assert bad.status_code == 400 and "time of day" in bad.json()["detail"]
    assert api.post("/api/schedule/approve", json={"medicines": [MEDICINE], "approved_by": " "}).status_code == 400
    schedule = approve(api)
    assert schedule["approved_by"] == "Daughter" and schedule["cells"]["1"] == [{"medicine_id": "m1", "count": 1}]


# ------------------------------------------------------------------ fill check


def test_fill_check_then_confirm_saves_reference_photos(api):
    approve(api)
    r = tray(api, "fill", "09:00").json()
    assert len(r["result"]["cells"]) == 28 and r["say"] == "fill_checked"
    assert api.get(r["view_url"]).status_code == 200  # the straightened photo is served
    saved = api.post("/api/tray/confirm", json={"by": "Daughter"}).json()["saved"]
    assert len(saved) == 1 and api.get(saved[0]["url"]).status_code == 200
    assert api.post("/api/tray/confirm", json={"by": "Daughter"}).status_code == 409  # only once


# ------------------------------------------------------------------ one dose


def test_dose_reminded_checked_and_taken(api):
    approve(api)
    pre = tray(api, "pre_dose", "12:31").json()
    assert pre["state"] == "open" and pre["say"] == "reminder" and pre["dose"]["cell"] == 1
    assert tray(api, "pre_dose", "12:32").json()["say"] == "already_started"
    out = close_lid(api, "12:40").json()
    assert out["kind"] == "dose" and out["result"]["result"] == "correct" and out["say"] == "well_done"
    assert dose_state(api) == "removed"
    log = [e["kind"] for e in api.get("/api/events").json()["log"]]
    assert log == ["reminder", "check"]


def test_click_mode_dose_opens_without_photo(api):
    approve(api)
    pre = tray(api, "pre_dose", "12:31", photo=False).json()
    assert pre["state"] == "open" and pre["result"] is None


def test_lid_closed_with_no_dose_open_alerts_the_family(api):
    approve(api)
    tray(api, "fill", "09:00")
    out = close_lid(api, "10:00").json()  # the fake changed_cells always reports compartment 1
    assert out["kind"] == "lid" and out["changed_cells"] == [1] and out["say"] == "not_time_yet"
    assert [a["reason"] for a in api.get("/api/events").json()["alerts"]] == ["lid_changed"]


# ------------------------------------------------------------------ hold, unsure pill, alerts


def test_pre_dose_problem_holds_the_dose_until_cleared(api, monkeypatch):
    approve(api)

    def wrong_pill(dose, matches, schedule):
        return T.TrayResult(cells=[T.CellStatus(cell=dose.cell, state=T.CellState.wrong,
                                                expected=schedule.cells[dose.cell], found=matches,
                                                note="Orange pill, label says white")])

    monkeypatch.setattr(pipelines, "check_tray", wrong_pill)
    pre = tray(api, "pre_dose", "12:31").json()
    assert pre["state"] == "on_hold" and pre["say"] == "please_wait"
    alerts = api.get("/api/events").json()["alerts"]
    assert alerts[0]["reason"] == "pre_dose_problem" and alerts[0]["message"] == "Orange pill, label says white"

    r = api.post(f"/api/doses/{NOON_DOSE}/clear", json={"reason": "tray_fixed", "by": "Daughter"}).json()
    assert r["state"] == "upcoming" and api.get("/api/events").json()["alerts"] == []
    monkeypatch.undo()
    assert tray(api, "pre_dose", "12:35").json()["state"] == "open"  # checked again after the fix
    assert api.post(f"/api/doses/{NOON_DOSE}/clear", json={"reason": "camera_wrong", "by": "D"}).status_code == 409


def test_unsure_pill_is_confirmed_by_the_family(api, monkeypatch):
    approve(api)
    tray(api, "pre_dose", "12:31")

    def unsure(dose, before, after, changed, schedule):
        taken = [m.model_copy(update={"certainty": T.Certainty.unsure}) for m in before if m.pill.cell == dose.cell]
        return T.CheckResult(dose=dose, result=T.DoseResult.unsure, taken=taken, message_key="checking")

    monkeypatch.setattr(pipelines, "check_dose", unsure)
    out = close_lid(api, "12:40").json()
    today = api.get("/api/events").json()
    assert out["result"]["result"] == "unsure" and today["waiting_checks"][0]["check_id"] == out["check_id"]
    assert today["alerts"][0]["reason"] == "unsure_pill"

    r = api.post(f"/api/checks/{out['check_id']}/answer", json={"confirm": True, "by": "Daughter"}).json()
    assert r["refs_saved"] == 1 and r["state"] == "removed"
    today = api.get("/api/events").json()
    assert today["waiting_checks"] == [] and today["alerts"] == []
    assert api.post(f"/api/checks/{out['check_id']}/answer", json={"confirm": True, "by": "D"}).status_code == 409


def test_tick_runs_alert_rules_and_late_dose_is_taken_late(api, monkeypatch):
    approve(api)
    tray(api, "pre_dose", "12:31")

    def rules(log, sim_time, settings):
        return [T.Action(kind="second_reminder", dose_id=NOON_DOSE, reason="late", message_key="second_reminder"),
                T.Action(kind="family_alert", dose_id=NOON_DOSE, reason="late", message_key="family_alert")]

    monkeypatch.setattr(pipelines, "alert_rules", rules)
    r = api.post("/api/events", json={"sim_time": f"{MON}T13:05"}).json()
    assert r["say"] == ["second_reminder"]
    alert = api.get("/api/events").json()["alerts"][0]
    assert alert["reason"] == "late"
    monkeypatch.undo()
    close_lid(api, "13:10")
    assert dose_state(api) == "taken_late"
    assert api.post(f"/api/alerts/{alert['id']}/handled").status_code == 200
    assert api.post(f"/api/alerts/{alert['id']}/handled").status_code == 404


def test_missed_dose(api, monkeypatch):
    approve(api)
    monkeypatch.setattr(pipelines, "alert_rules", lambda log, t, s: [
        T.Action(kind="mark_missed", dose_id=NOON_DOSE, reason="missed", message_key="")])
    api.post("/api/events", json={"sim_time": f"{MON}T18:31"})
    assert dose_state(api) == "missed"


# ------------------------------------------------------------------ voice and refill


def test_ask_answers_or_falls_back_in_time(api, monkeypatch):
    approve(api)
    assert api.post("/api/ask", json={"question": "Did I take my noon pills?", "language": "en"}).json()["fallback"]
    monkeypatch.setattr(main, "ASK_TIMEOUT_S", 0.2)
    monkeypatch.setattr(pipelines, "answer", lambda *a: time.sleep(1))
    r = api.post("/api/ask", json={"question": "我的下一個藥是什麼？", "language": "zh-TW"}).json()
    assert r["fallback"] and r["language"] == "zh-TW"
    assert api.post("/api/ask", json={"question": "", "language": "en"}).status_code == 422


def test_new_prescription_stops_the_schedule(api):
    approve(api)
    assert api.post("/api/refill", json={"kind": "refill"}).json()["next"] == "guided_filling"
    assert api.post("/api/refill", json={"kind": "new_prescription"}).json()["next"] == "label_photo"
    assert api.get("/api/schedule").status_code == 409
