"""Image preprocessing: label cleanup, tray straightening, change detection (WBS 3.1, 4.1, 4.2).

Owner: 李佳修 Joshua. Signatures: packages/medbag_common/src/medbag_common/interfaces.py

For now every function below is the stub from medbag_common.stubs, so the server already works.
Replace them one by one with your real code (a file per function is fine, e.g. preprocess_label.py),
keep the exact names and parameters, and run:
    MEDBAG_IMPL=prep uv run pytest packages/medbag_common/tests
Add the libraries you need with:  uv add --package prep opencv-python
"""

from medbag_common.stubs import preprocess_label, rectify, changed_cells  # TODO: replace with real code

__all__ = ['preprocess_label', 'rectify', 'changed_cells']
