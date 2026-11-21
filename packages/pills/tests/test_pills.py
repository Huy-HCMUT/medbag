"""Your own tests for pills (agreement tests live in packages/medbag_common/tests)."""

import pills


def test_exports():
    for fn in ['detect_pills']:
        assert callable(getattr(pills, fn))
