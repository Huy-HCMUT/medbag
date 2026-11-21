"""The fake results follow the rulebook (each package runs the same check in its own tests)."""

from medbag_common import types as T
from medbag_common.agreement import DOSE, SCHEDULE, check_package


def test_fake_results_follow_the_rulebook():
    check_package("medbag_common.fake_results")


def test_schedule_helper():
    assert [e.medicine_id for e in SCHEDULE.cells[DOSE.cell]] == ["m1"]
    assert sum(len(v) for v in SCHEDULE.cells.values()) == 7  # noon on 7 days
    assert T.cell_box(5) == T.Box(x=160, y=160, w=160, h=160)  # Tuesday noon
