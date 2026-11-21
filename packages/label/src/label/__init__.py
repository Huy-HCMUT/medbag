"""label (Sam): one file per function. Open the file and write your code there.

Test your package:  uv run pytest packages/label
Add a library:      uv add --package label google-genai pytesseract
"""

from .read_label import read_label
from .check_fields import check_fields

__all__ = ['read_label', 'check_fields']
