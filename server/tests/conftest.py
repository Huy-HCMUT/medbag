"""Server tests use a fresh database and photo folder in a temporary place, never data/."""

import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="medbag_test_"))
os.environ["MEDBAG_DB"] = str(_tmp / "test.db")
os.environ["MEDBAG_PHOTOS"] = str(_tmp / "photos")
