"""Pill detection with YOLO26n on the straightened tray (WBS 4.3).

Owner: 鄂弘 Alex. Signatures: packages/medbag_common/src/medbag_common/interfaces.py

For now every function below is a fake result from medbag_common.fake_results, so the server already works.
Replace them one by one with your real code (a file per function is fine, e.g. detect_pills.py),
keep the exact names and parameters, and run:
    MEDBAG_IMPL=pills uv run pytest packages/medbag_common/tests   # agreement test
Add the libraries you need with:  uv add --package pills ultralytics
"""

from medbag_common.fake_results import detect_pills  # TODO: replace with real code

__all__ = ['detect_pills']
