"""pills (Alex): one file per function. Open the file and write your code there.

Test your package:  uv run pytest packages/pills
Add a library:      uv add --package pills ultralytics
"""

from .detect_pills import detect_pills

__all__ = ['detect_pills']
