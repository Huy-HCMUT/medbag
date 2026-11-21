"""Fingerprints, identification, fill/pre-dose/dose checks, alert rules (WBS 4.4-4.8).

Owner: 劉亮萱 Emily. Signatures: packages/medbag_common/src/medbag_common/interfaces.py

For now every function below is a fake result from medbag_common.fake_results, so the server already works.
Replace them one by one with your real code (a file per function is fine, e.g. fingerprint.py),
keep the exact names and parameters, and run:
    MEDBAG_IMPL=check uv run pytest packages/medbag_common/tests   # agreement test
Add the libraries you need with:  uv add --package check opencv-python
"""

from medbag_common.fake_results import fingerprint, identify, match_fill, check_tray, check_dose, alert_rules  # TODO: replace with real code

__all__ = ['fingerprint', 'identify', 'match_fill', 'check_tray', 'check_dose', 'alert_rules']
