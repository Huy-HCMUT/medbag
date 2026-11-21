"""check_fields (Sam). Write your code in this function; keep the name and the parameters.

What it takes in and gives back: packages/medbag_common/README.md (the function table)
and packages/medbag_common/examples/check_fields.json (a real example).
Test:  uv run pytest packages/label
"""

from __future__ import annotations

from medbag_common import fake_results
from medbag_common.types import LabelResult


def check_fields(result: LabelResult) -> LabelResult:
    """Same LabelResult with rule problems added to flags.

    Pipeline 1 (SP1). E.g. 每日 2 次 with 1 slot -> frequency_slots_mismatch;
    a missing field -> missing_field; 10 pills a time -> impossible_dose.
    """
    # TODO(Sam): replace the line below with your real code.
    return fake_results.check_fields(result)
