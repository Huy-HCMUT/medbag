"""For each function name, gives the real function or the fake result, as set in config.USE_REAL."""

import importlib

from medbag_common import fake_results

from .config import USE_REAL

OWNER_PACKAGE = {
    "preprocess_label": "prep", "rectify": "prep", "changed_cells": "prep",
    "read_label": "label", "check_fields": "label",
    "detect_pills": "pills", "answer": "voice",
    "fingerprint": "check", "identify": "check", "match_fill": "check",
    "check_tray": "check", "check_dose": "check", "alert_rules": "check",
}


def get(name: str):
    if USE_REAL.get(name):
        return getattr(importlib.import_module(OWNER_PACKAGE[name]), name)
    return getattr(fake_results, name)
