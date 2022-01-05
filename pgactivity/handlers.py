from typing import Optional

from blessed.keyboard import Keystroke

from . import keys
from .types import DurationMode, Flag, QueryMode, SortKey, enum_next


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


def duration_mode(key: Keystroke, mode: DurationMode) -> DurationMode:
    """Return the updated duration mode matching input key.

    >>> from blessed.keyboard import Keystroke as k

    >>> duration_mode(k("42"), DurationMode.query).name
    'query'
    >>> duration_mode(k("T"), DurationMode.transaction).name
    'backend'
    """
    if key == keys.CHANGE_DURATION_MODE:
        return enum_next(mode)
    return mode


def wrap_query(key: Keystroke, wrap: bool) -> bool:
    """Return the updated 'wrap' value depending on input key.

    >>> from blessed.keyboard import Keystroke as k

    >>> wrap_query(k("42"), True)
    True
    >>> wrap_query(k("v"), False)
    True
    """
    if key == keys.WRAP_QUERY:
        return not wrap
    return wrap


def query_mode(key: Keystroke) -> Optional[QueryMode]:
    """Return the query mode matching input key or None.

    >>> import curses
    >>> from blessed.keyboard import Keystroke as k

    >>> query_mode(k("42"))
    >>> query_mode(k("1")).name
    'activities'
    >>> query_mode(k(code=curses.KEY_F3)).name
    'blocking'
    """
    if key.is_sequence:
        try:
            return keys.QUERYMODE_FROM_KEYS[key.code]
        except KeyError:
            pass
    return keys.QUERYMODE_FROM_KEYS.get(key)


def sort_key_for(
    key: Keystroke, query_mode: QueryMode, flag: Flag
) -> Optional[SortKey]:
    """Return the sort key matching input key or None.

    >>> from blessed.keyboard import Keystroke as k
    >>> from pgactivity.types import QueryMode

    >>> flag = Flag.all()

    Unhandled key:
    >>> sort_key_for(k("1"), QueryMode.activities, flag)

    In activities mode, 'm', 'w', 't', ... keys are handled:
    >>> sort_key_for(k("m"), QueryMode.activities, flag).name
    'mem'
    >>> sort_key_for(k("w"), QueryMode.activities, flag).name
    'write'
    >>> sort_key_for(k("t"), QueryMode.activities, flag).name
    'duration'
    >>> sort_key_for(k("c"), QueryMode.activities, flag).name
    'cpu'

    In other modes, the default sort key is always returned:
    >>> sort_key_for(k("m"), QueryMode.waiting, flag).name
    'duration'

    When flag does not match given sort key, return None:
    >>> flag ^= Flag.CPU
    >>> sort_key_for(k("c"), QueryMode.activities, flag)
    >>> sort_key_for(k("m"), QueryMode.activities, flag).name
    'mem'
    >>> flag ^= Flag.MEM
    >>> sort_key_for(k("m"), QueryMode.activities, flag)
    """
    if query_mode != QueryMode.activities:
        return SortKey.default()
    try:
        sort_key, required_flag = {
            keys.SORTBY_CPU: (SortKey.cpu, Flag.CPU),
            keys.SORTBY_MEM: (SortKey.mem, Flag.MEM),
            keys.SORTBY_READ: (SortKey.read, Flag.READ),
            keys.SORTBY_TIME: (SortKey.duration, Flag.TIME),
            keys.SORTBY_WRITE: (SortKey.write, Flag.WRITE),
        }[key]
    except KeyError:
        return None
    if flag & required_flag:
        return sort_key
    return None
