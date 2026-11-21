"""Tests for check. Run:  uv run pytest packages/check"""

from medbag_common.agreement import check_package


def test_follows_the_rulebook():
    """Your functions have the agreed names, parameters and outputs, and fit with everyone else's."""
    check_package("check")


# Add your own tests below, e.g. run your function on photos from data/test_set/ and check the result.
