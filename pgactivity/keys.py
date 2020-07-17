from typing import List, Tuple


EXIT = "q"
HELP = "h"
REFRESH_TIME_INCREASE = "+"
REFRESH_TIME_DECREASE = "-"

BINDINGS: List[Tuple[str, str]] = [
    ("Up/Down", "scroll process list"),
    ("C", "activate/deactivate colors"),
    ("Space", "pause"),
    ("r", "sort by READ/s desc. (activities)"),
    ("v", "change display mode"),
    ("w", "sort by WRITE/s desc. (activities)"),
    (EXIT, "quit"),
    (REFRESH_TIME_INCREASE, "increase refresh time (max:5s)"),
    ("m", "sort by MEM% desc. (activities)"),
    (REFRESH_TIME_DECREASE, "decrease refresh time (min:0.5s)"),
    ("t", "sort by TIME+ desc. (activities)"),
    ("R", "force refresh"),
    ("T", "change duration mode"),
    ("D", "force refresh database size"),
]

MODES: List[Tuple[str, str]] = [
    ("F1/1", "running queries"),
    ("F2/2", "waiting queries"),
    ("F3/3", "blocking queries"),
]
