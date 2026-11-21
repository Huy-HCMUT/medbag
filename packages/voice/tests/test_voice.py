"""Your own tests for voice (agreement tests live in packages/medbag_common/tests)."""

import voice


def test_exports():
    assert callable(voice.answer)
