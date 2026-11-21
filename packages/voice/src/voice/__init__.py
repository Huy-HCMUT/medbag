"""Voice questions answered with Gemini, only from her schedule and log (WBS 4.11, Should).

Owner: 鄂弘 Alex. Signature: packages/medbag_common/src/medbag_common/interfaces.py (AnswerQuestion)

For now answer() is a fake result from medbag_common.fake_results, so the server already works.
Replace it with your real code (e.g. answer.py), keep the exact name and parameters, and run:
    MEDBAG_IMPL=voice uv run pytest packages/medbag_common/tests   # agreement test
Add the libraries you need with:  uv add --package voice google-genai
"""

from medbag_common.fake_results import answer  # TODO: replace with real code

__all__ = ['answer']
