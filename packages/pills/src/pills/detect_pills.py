"""detect_pills (Alex). Write your code in this function; keep the name and the parameters.

What it takes in and gives back: packages/medbag_common/README.md (the function table)
and packages/medbag_common/examples/detect_pills.json (a real example).
Test:  uv run pytest packages/pills
"""

from __future__ import annotations

from typing import Any

from medbag_common import fake_results
from medbag_common.types import Pill, TrayView


def detect_pills(view: TrayView, model: Any) -> list[Pill]:
    """Straightened tray -> every pill on it, each with its compartment (YOLO26n, one class).

    Pipelines 2 and 3. Runs once on view.image (the same kind of picture as the training
    annotations in WBS 2.5) and gives each pill the compartment whose cell_box holds the
    box centre. `model` is the YOLO26n model the server loaded at start-up.
    """
    # TODO(Alex): replace the line below with your real code.
    return fake_results.detect_pills(view, model)
