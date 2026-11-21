"""Your own tests for check (agreement tests live in packages/medbag_common/tests)."""

import check


def test_exports():
    for fn in ['fingerprint', 'identify', 'match_fill', 'check_tray', 'check_dose', 'alert_rules']:
        assert callable(getattr(check, fn))
