"""answer (Alex). Write your code in this function; keep the name and the parameters.

What it takes in and gives back: packages/medbag_common/README.md (the function table)
and packages/medbag_common/examples/answer.json (a real example).
Test:  uv run pytest packages/voice
"""

from __future__ import annotations

from typing import Any

from medbag_common import fake_results
from medbag_common.types import Answer, LogEntry, Schedule


def answer(
    question: str,
    schedule: Schedule,
    log: list[LogEntry],
    language: str,
    gemini: Any,
) -> Answer:
    """Spoken question -> answer text, only from her schedule and log (Should, SP8).

    Return fallback = True with the scripted line when Gemini is None, slow (5 s) or the
    answer fails the keyword safety check (dose, extra, stop ...).
    """
    # TODO(Alex): replace the line below with your real code.
    return fake_results.answer(question, schedule, log, language, gemini)
