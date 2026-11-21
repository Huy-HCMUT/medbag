"""Pill detection with YOLO26n; voice questions (WBS 4.3, 4.11).

Owner: 鄂弘 Alex. Signatures: packages/medbag_common/src/medbag_common/interfaces.py

For now every function below is the stub from medbag_common.stubs, so the server already works.
Replace them one by one with your real code (a file per function is fine, e.g. detect_pills.py),
keep the exact names and parameters, and run:
    MEDBAG_IMPL=pills uv run pytest packages/medbag_common/tests
Add the libraries you need with:  uv add --package pills ultralytics
"""

from medbag_common.stubs import detect_pills, answer  # TODO: replace with real code

__all__ = ['detect_pills', 'answer']
