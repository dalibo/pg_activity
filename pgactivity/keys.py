import curses
from typing import Any, List, Optional, Tuple

import attr

from .types import QueryMode


EXIT = "q"
EXIT_DEBUG = "z"
HELP = "h"
PAUSE = " "
REFRESH_TIME_INCREASE = "+"
REFRESH_TIME_DECREASE = "-"
SORTBY_READ = "r"
SORTBY_WRITE = "w"
SORTBY_MEM = "m"
SORTBY_TIME = "t"
SORTBY_CPU = "c"


@attr.s(auto_attribs=True, frozen=True, slots=True)
class Key:
    value: str
    description: str
    name: Optional[str] = None

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, str):
            return False
        return self.value == other


BINDINGS: List[Key] = [
    Key("Up/Down", "scroll process list"),
    Key("C", "activate/deactivate colors"),
    Key(PAUSE, "pause", "Space"),
    Key(SORTBY_READ, "sort by READ/s desc. (activities)"),
    Key("v", "change display mode"),
    Key(SORTBY_WRITE, "sort by WRITE/s desc. (activities)"),
    Key(EXIT, "quit"),
    Key(REFRESH_TIME_INCREASE, "increase refresh time (max:5s)"),
    Key(SORTBY_CPU, "sort by CPU% desc. (activities)"),
    Key(SORTBY_MEM, "sort by MEM% desc. (activities)"),
    Key(REFRESH_TIME_DECREASE, "decrease refresh time (min:0.5s)"),
    Key(SORTBY_TIME, "sort by TIME+ desc. (activities)"),
    Key("R", "force refresh"),
    Key("T", "change duration mode"),
    Key("D", "force refresh database size"),
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


MODES: List[Key] = [
    Key("/".join(KEYS_BY_QUERYMODE[qm][:-1]), qm.value) for qm in QueryMode
]
