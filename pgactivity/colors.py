from . import utils


FIELD_BY_MODE = {
    "pid": {"default": "cyan", "cursor": "cyan_reverse", "yellow": "yellow_bold"},
    "database": {
        "default": "black_bold",
        "cursor": "cyan_reverse",
        "yellow": "yellow_bold",
    },
    "application_name": {
        "default": "black_bold",
        "cursor": "cyan_reverse",
        "yellow": "yellow_bold",
    },
    "user": {
        "default": "black_bold",
        "cursor": "cyan_reverse",
        "yellow": "yellow_bold",
    },
    "client": {"default": "cyan", "cursor": "cyan_reverse", "yellow": "yellow_bold"},
    "cpu": {"default": "normal", "cursor": "cyan_reverse", "yellow": "yellow_bold"},
    "mem": {"default": "normal", "cursor": "cyan_reverse", "yellow": "yellow_bold"},
    "read": {"default": "normal", "cursor": "cyan_reverse", "yellow": "yellow_bold"},
    "write": {"default": "normal", "cursor": "cyan_reverse", "yellow": "yellow_bold"},
    "time_red": {"default": "red", "cursor": "cyan_reverse", "yellow": "yellow_bold"},
    "time_yellow": {
        "default": "yellow",
        "cursor": "cyan_reverse",
        "yellow": "yellow_bold",
    },
    "time_green": {
        "default": "green",
        "cursor": "cyan_reverse",
        "yellow": "yellow_bold",
    },
    "wait_green": {
        "default": "green_bold",
        "cursor": "cyan_reverse",
        "yellow": "yellow_bold",
    },
    "wait_red": {
        "default": "red_bold",
        "cursor": "cyan_reverse",
        "yellow": "yellow_bold",
    },
    "state_default": {
        "default": "normal",
        "cursor": "cyan_reverse",
        "yellow": "yellow_bold",
    },
    "state_yellow": {
        "default": "yellow",
        "cursor": "cyan_reverse",
        "yellow": "yellow_bold",
    },
    "state_green": {
        "default": "green",
        "cursor": "cyan_reverse",
        "yellow": "yellow_bold",
    },
    "state_red": {"default": "red", "cursor": "cyan_reverse", "yellow": "yellow_bold"},
    "query": {"default": "normal", "cursor": "cyan_reverse", "yellow": "yellow_bold"},
    "relation": {"default": "cyan", "cursor": "cyan_reverse", "yellow": "yellow_bold"},
    "type": {"default": "normal", "cursor": "cyan_reverse", "yellow": "yellow_bold"},
    "mode_yellow": {
        "default": "yellow_bold",
        "cursor": "cyan_reverse",
        "yellow": "yellow_bold",
    },
    "mode_red": {
        "default": "red_bold",
        "cursor": "cyan_reverse",
        "yellow": "yellow_bold",
    },
}


def short_state(state: str) -> str:
    state = utils.short_state(state)
    if state == "active":
        return "state_green"
    elif state == "idle in trans":
        return "state_yellow"
    elif state == "idle in trans (a)":
        return "state_red"
    else:
        return "state_default"


def lock_mode(mode: str) -> str:
    if mode in (
        "ExclusiveLock",
        "RowExclusiveLock",
        "AccessExclusiveLock",
    ):
        return "mode_red"
    else:
        return "mode_yellow"


def wait(value: bool) -> str:
    return "wait_red" if value else "wait_green"
