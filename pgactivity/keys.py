import curses
from typing import List, Tuple

from .types import QueryMode


EXIT = "q"
HELP = "h"
REFRESH_TIME_INCREASE = "+"
REFRESH_TIME_DECREASE = "-"
SORTBY_READ = "r"
SORTBY_WRITE = "w"
SORTBY_MEM = "m"
SORTBY_TIME = "t"
SORTBY_CPU = "c"

BINDINGS: List[Tuple[str, str]] = [
    ("Up/Down", "scroll process list"),
    ("C", "activate/deactivate colors"),
    ("Space", "pause"),
    (SORTBY_READ, "sort by READ/s desc. (activities)"),
    ("v", "change display mode"),
    (SORTBY_WRITE, "sort by WRITE/s desc. (activities)"),
    (EXIT, "quit"),
    (REFRESH_TIME_INCREASE, "increase refresh time (max:5s)"),
    (SORTBY_CPU, "sort by CPU% desc. (activities)"),
    (SORTBY_MEM, "sort by MEM% desc. (activities)"),
    (REFRESH_TIME_DECREASE, "decrease refresh time (min:0.5s)"),
    (SORTBY_TIME, "sort by TIME+ desc. (activities)"),
    ("R", "force refresh"),
    ("T", "change duration mode"),
    ("D", "force refresh database size"),
]


def _sequence_by_int(v: int) -> Tuple[str, str, int]:
    """
    >>> _sequence_by_int(11)
    ('F11', '11', 275)
    """
    assert 1 <= v <= 12, v
    return f"F{v}", str(v), getattr(curses, f"KEY_F{v}")


KEYS_BY_QUERYMODE = {
    QueryMode.activities: _sequence_by_int(1),
    QueryMode.waiting: _sequence_by_int(2),
    QueryMode.blocking: _sequence_by_int(3),
}
QUERYMODE_FROM_KEYS = {
    k: qm for qm, keys in KEYS_BY_QUERYMODE.items() for k in keys[1:]
}


MODES: List[Tuple[str, str]] = [
    ("/".join(KEYS_BY_QUERYMODE[qm][:-1]), qm.value) for qm in QueryMode
]
