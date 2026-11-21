"""Your own tests for label (agreement tests live in packages/medbag_common/tests)."""

import label


def test_exports():
    for fn in ['read_label', 'check_fields']:
        assert callable(getattr(label, fn))
