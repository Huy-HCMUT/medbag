"""Label reading: Gemini with Tesseract fallback, field rule checks (WBS 3.3-3.5).

Owner: 王有財 Sam. Signatures: packages/medbag_common/src/medbag_common/interfaces.py

For now every function below is the stub from medbag_common.stubs, so the server already works.
Replace them one by one with your real code (a file per function is fine, e.g. read_label.py),
keep the exact names and parameters, and run:
    MEDBAG_IMPL=label uv run pytest packages/medbag_common/tests
Add the libraries you need with:  uv add --package label google-genai pytesseract
"""

from medbag_common.stubs import read_label, check_fields  # TODO: replace with real code

__all__ = ['read_label', 'check_fields']
