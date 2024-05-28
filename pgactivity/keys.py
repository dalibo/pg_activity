from __future__ import annotations

import curses
from typing import Any

import attr
from blessed.keyboard import Keystroke

from .types import QueryMode


@attr.s(auto_attribs=True, frozen=True, slots=True)
class Key:
    value: str
    description: str
    name: str | None = None
    local_only: bool = False

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, str):
            return False
        return self.value == other


CANCEL_SELECTION = "KEY_ESCAPE"
CHANGE_DURATION_MODE = "T"
WRAP_QUERY = "v"
EXIT = "q"
HELP = "h"
SPACE = " "
COPY_TO_CLIPBOARD = "y"
PROCESS_CANCEL = "C"
PROCESS_KILL = "K"
PROCESS_FIRST = "KEY_HOME"
PROCESS_NEXT = "KEY_DOWN"
PROCESS_NEXTPAGE = "KEY_PGDOWN"
PROCESS_NEXT_VI = "j"
PROCESS_PREV = "KEY_UP"
PROCESS_PREV_VI = "k"
PROCESS_PREVPAGE = "KEY_PGUP"
PROCESS_LAST = "KEY_END"
PROCESS_PIN = Key(SPACE, "tag/untag current query", "Space")
REFRESH_DB_SIZE = "D"
REFRESH_TIME_INCREASE = "+"
REFRESH_TIME_DECREASE = "-"
SORTBY_READ = "r"
SORTBY_WRITE = "w"
SORTBY_MEM = "m"
SORTBY_TIME = "t"
SORTBY_CPU = "c"
HEADER_TOGGLE_SYSTEM = "s"
HEADER_TOGGLE_INSTANCE = "i"
HEADER_TOGGLE_WORKERS = "o"


def is_process_next(key: Keystroke) -> bool:
    if key.name == PROCESS_NEXT:
        return True
    elif key == PROCESS_NEXT_VI:
        return True
    return False


def is_process_prev(key: Keystroke) -> bool:
    if key.name == PROCESS_PREV:
        return True
    elif key == PROCESS_PREV_VI:
        return True
    return False


def is_process_nextpage(key: Keystroke) -> bool:
    return key.name == PROCESS_NEXTPAGE


def is_process_prevpage(key: Keystroke) -> bool:
    return key.name == PROCESS_PREVPAGE


def is_process_first(key: Keystroke) -> bool:
    return key.name == PROCESS_FIRST


def is_process_last(key: Keystroke) -> bool:
    return key.name == PROCESS_LAST


def is_toggle_header_system(key: Keystroke) -> bool:
    return key == HEADER_TOGGLE_SYSTEM


def is_toggle_header_instance(key: Keystroke) -> bool:
    return key == HEADER_TOGGLE_INSTANCE


def is_toggle_header_workers(key: Keystroke) -> bool:
    return key == HEADER_TOGGLE_WORKERS


EXIT_KEY = Key(EXIT, "quit")
PAUSE_KEY = Key(SPACE, "pause/unpause", "Space")

BINDINGS: list[Key] = [
    Key("Up/Down", "scroll process list"),
    PAUSE_KEY,
    Key(SORTBY_CPU, "sort by CPU% desc. (activities)", local_only=True),
    Key(SORTBY_MEM, "sort by MEM% desc. (activities)", local_only=True),
    Key(SORTBY_READ, "sort by READ/s desc. (activities)", local_only=True),
    Key(SORTBY_WRITE, "sort by WRITE/s desc. (activities)", local_only=True),
    Key(SORTBY_TIME, "sort by TIME+ desc. (activities)", local_only=True),
    Key(REFRESH_TIME_INCREASE, "increase refresh time (max:5s)"),
    Key(REFRESH_TIME_DECREASE, "decrease refresh time (min:0.5s)"),
    Key(WRAP_QUERY, "toggle query wrap"),
    Key(CHANGE_DURATION_MODE, "change duration mode"),
    Key(REFRESH_DB_SIZE, "force refresh database size"),
    Key("R", "force refresh"),
    Key(HEADER_TOGGLE_SYSTEM, "Display system information in header", local_only=True),
    Key(HEADER_TOGGLE_INSTANCE, "Display general instance information in header"),
    Key(HEADER_TOGGLE_WORKERS, "Display worker information in header"),
    EXIT_KEY,
]


def _sequence_by_int(v: int) -> tuple[str, str, int]:
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


MODES: list[Key] = [
    Key("/".join(KEYS_BY_QUERYMODE[qm][:-1]), qm.value) for qm in QueryMode
]
