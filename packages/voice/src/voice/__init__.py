"""voice (Alex): one file per function. Open the file and write your code there.

Test your package:  uv run pytest packages/voice
Add a library:      uv add --package voice google-genai
"""

from .answer import answer

__all__ = ['answer']
