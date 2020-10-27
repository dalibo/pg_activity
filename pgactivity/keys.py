import curses
from typing import Any, List, Optional, Tuple

import attr

from .types import QueryMode


CANCEL_SELECTION = "KEY_ESCAPE"
CHANGE_DURATION_MODE = "T"
CHANGE_DISPLAY_MODE = "v"
EXIT = "q"
HELP = "h"
PAUSE = " "
PROCESS_NEXT = "KEY_DOWN"
PROCESS_PREV = "KEY_UP"
REFRESH_DB_SIZE = "D"
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
    local_only: bool = False

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, str):
            return False
        return self.value == other


EXIT_KEY = Key(EXIT, "quit")
PAUSE_KEY = Key(PAUSE, "pause", "Space")

BINDINGS: List[Key] = [
    Key("Up/Down", "scroll process list"),
    PAUSE_KEY,
    Key(SORTBY_READ, "sort by READ/s desc. (activities)", local_only=True),
    Key(CHANGE_DISPLAY_MODE, "change display mode"),
    Key(SORTBY_WRITE, "sort by WRITE/s desc. (activities)", local_only=True),
    EXIT_KEY,
    Key(REFRESH_TIME_INCREASE, "increase refresh time (max:5s)"),
    Key(SORTBY_CPU, "sort by CPU% desc. (activities)", local_only=True),
    Key(SORTBY_MEM, "sort by MEM% desc. (activities)", local_only=True),
    Key(REFRESH_TIME_DECREASE, "decrease refresh time (min:0.5s)"),
    Key(SORTBY_TIME, "sort by TIME+ desc. (activities)", local_only=True),
    Key("R", "force refresh"),
    Key(CHANGE_DURATION_MODE, "change duration mode"),
    Key(REFRESH_DB_SIZE, "force refresh database size"),
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
