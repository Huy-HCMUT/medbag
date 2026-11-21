"""identify (Emily). Write your code in this function; keep the name and the parameters.

What it takes in and gives back: packages/medbag_common/README.md (the function table)
and packages/medbag_common/examples/identify.json (a real example).
Test:  uv run pytest packages/check
"""

from __future__ import annotations

from medbag_common import fake_results
from medbag_common.types import Match, Pill, RefPhoto, TrayView


def identify(view: TrayView, pill: Pill, refs: list[RefPhoto]) -> Match:
    """One pill -> which medicine it is, with sure, unsure or no_match.

    Pipeline 3 (SP4, SP6). Compares the pill's fingerprint with the fingerprints in `refs`
    (never opens RefPhoto.path) and returns that fingerprint in Match.fingerprint, so the
    server can save the pill as a new reference when the family confirms an unsure one (SP9).
    """
    # TODO(Emily): replace the line below with your real code.
    return fake_results.identify(view, pill, refs)
