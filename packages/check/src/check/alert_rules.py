"""alert_rules (Emily). Write your code in this function; keep the name and the parameters.

What it takes in and gives back: packages/medbag_common/README.md (the function table)
and packages/medbag_common/examples/alert_rules.json (a real example).
Test:  uv run pytest packages/check
"""

from __future__ import annotations

from datetime import datetime

from medbag_common import fake_results
from medbag_common.types import Action, LogEntry, Settings


def alert_rules(log: list[LogEntry], sim_time: datetime, settings: Settings) -> list[Action]:
    """Dose log and the simulator's time -> what the server should do now (Pipeline 4, SP7).

    Second reminder after 15 min, family alert after 30 min, wrong pill not put back
    after 2 min, missed at the next dose time. Nothing while a dose is on hold.
    Each action once: skip one that is already in the log.
    """
    # TODO(Emily): replace the line below with your real code.
    return fake_results.alert_rules(log, sim_time, settings)
