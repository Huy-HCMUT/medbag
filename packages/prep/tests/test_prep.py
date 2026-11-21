"""Your own tests for prep (contract tests live in packages/medbag_common/tests)."""

import prep


def test_exports():
    for fn in ['preprocess_label', 'rectify', 'changed_cells']:
        assert callable(getattr(prep, fn))
