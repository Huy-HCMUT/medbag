"""Picks the real method or the stub for each name, as set in config.USE_REAL."""

import importlib

from medbag_common import stubs

from .config import USE_REAL

OWNER_PACKAGE = {
    "preprocess_label": "prep", "rectify": "prep", "changed_cells": "prep",
    "read_label": "label", "check_fields": "label",
    "detect_pills": "pills", "answer": "pills",
    "fingerprint": "check", "identify": "check", "match_fill": "check",
    "check_tray": "check", "check_dose": "check", "alert_rules": "check",
}


def get(name: str):
    if USE_REAL.get(name):
        return getattr(importlib.import_module(OWNER_PACKAGE[name]), name)
    return getattr(stubs, name)
