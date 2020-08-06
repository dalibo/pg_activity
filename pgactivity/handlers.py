from typing import Optional

from blessed.keyboard import Keystroke

from . import keys
from .types import QueryMode, SortKey


def refresh_time(
    key: Optional[str], value: float, minimum: float = 0.5, maximum: float = 5
) -> float:
    """Return an updated refresh time interval from input key respecting bounds.

    >>> refresh_time("+", 1)
    2
    >>> refresh_time("+", 5)
    5
    >>> refresh_time("+", 5, maximum=10)
    6
    >>> refresh_time("-", 2)
    1
    >>> refresh_time("-", 1)
    0.5
    >>> refresh_time("-", 0.5)
    0.5
    >>> refresh_time("=", 42)
    Traceback (most recent call last):
        ...
    ValueError: =
    """
    if key == keys.REFRESH_TIME_DECREASE:
        return max(value - 1, minimum)
    elif key == keys.REFRESH_TIME_INCREASE:
        return min(int(value + 1), maximum)
    raise ValueError(key)


def query_mode(key: Keystroke) -> Optional[QueryMode]:
    """Return the query mode matching input key or None.

    >>> import curses
    >>> from blessed.keyboard import Keystroke as k

    >>> query_mode(k("42"))
    >>> query_mode(k("1"))
    <QueryMode.activities: 'running queries'>
    >>> query_mode(k(code=curses.KEY_F3))
    <QueryMode.blocking: 'blocking queries'>
    """
    if key.is_sequence and key.code in keys.QUERYMODE_FROM_KEYS:
        key = key.code
    return keys.QUERYMODE_FROM_KEYS.get(key)


def sort_key_for(key: Keystroke, query_mode: QueryMode) -> Optional[SortKey]:
    """Return the sort key matching input key or None.

    >>> from blessed.keyboard import Keystroke as k
    >>> from pgactivity.types import QueryMode

    >>> sort_key_for(k("1"), QueryMode.activities)
    >>> sort_key_for(k("m"), QueryMode.activities)
    <SortKey.mem: 2>
    >>> sort_key_for(k("t"), QueryMode.activities)
    <SortKey.time: 5>
    >>> sort_key_for(k("m"), QueryMode.waiting)
    <SortKey.time: 5>
    """
    if query_mode != QueryMode.activities:
        return SortKey.default()
    return {
        keys.SORTBY_MEM: SortKey.mem,
        keys.SORTBY_READ: SortKey.read,
        keys.SORTBY_TIME: SortKey.time,
        keys.SORTBY_WRITE: SortKey.write,
    }.get(key)
