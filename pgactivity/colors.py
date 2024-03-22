from __future__ import annotations

from . import utils

PINNED_COLOR = "bold_yellow"
FOCUSED_COLOR = "cyan_reverse"


def short_state(state: str) -> str | None:
    state = utils.short_state(state)
    if state == "active":
        return "green"
    elif state == "idle in trans":
        return "yellow"
    elif state == "idle in trans (a)":
        return "red"
    return None


def lock_mode(mode: str) -> str:
    if mode in (
        "ExclusiveLock",
        "RowExclusiveLock",
        "AccessExclusiveLock",
    ):
        return "bold_red"
    else:
        return "bold_yellow"


def wait(value: bool) -> str:
    return "red" if value else "green"
