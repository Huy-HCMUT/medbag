"""Checks data/manifest.json (WBS 2.4): every situation is complete, and every filled-in photo exists."""

import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"
MANIFEST = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
CASES = {c["id"]: c for c in MANIFEST["cases"]}
KEYS = {"id", "group", "situation", "endpoint", "photo", "suggested_file", "expected", "demo", "priority"}


def test_ids_unique():
    assert len(CASES) == len(MANIFEST["cases"])


def test_every_case_complete():
    for c in CASES.values():
        assert KEYS <= c.keys(), c["id"]
        assert c["group"] in {"fill_check", "pre_dose", "dose"}, c["id"]


def test_before_photos_point_to_pre_dose_cases():
    for c in CASES.values():
        if "before" in c:
            assert CASES[c["before"]]["group"] == "pre_dose", c["id"]


def test_filled_photos_exist():
    for c in CASES.values():
        if c["photo"]:
            assert (DATA / c["photo"]).exists(), f'{c["id"]}: {c["photo"]} not found in data/'
