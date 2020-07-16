from textwrap import dedent
from typing import Iterable, Tuple

from blessed import Terminal

from .keys import BINDINGS, MODES


def help(term: Terminal, version: str) -> None:
    """Render help menu.

    >>> term = Terminal()
    >>> help(term, "2.1")
    pg_activity 2.1 - https://github.com/dalibo/pg_activity
    Released under PostgreSQL License.
    <BLANKLINE>
       Up/Down: scroll process list
             C: activate/deactivate colors
         Space: pause
             r: sort by READ/s desc. (activities)
             v: change display mode
             w: sort by WRITE/s desc. (activities)
             q: quit
             +: increase refresh time (max:5s)
             m: sort by MEM% desc. (activities)
             -: decrease refresh time (min:0.5s)
             t: sort by TIME+ desc. (activities)
             R: force refresh
             T: change duration mode
             D: force refresh database size
    Mode
          F1/1: running queries
          F2/2: waiting queries
          F3/3: blocking queries
    <BLANKLINE>
    Press any key to exit.
    """
    intro = dedent(
        f"""\
    {term.bold_green}pg_activity {version} - https://github.com/dalibo/pg_activity
    {term.normal}Released under PostgreSQL License.
    """
    )

    def render_mapping(keys: Iterable[Tuple[str, str]]) -> str:
        return "\n".join(
            f"{term.bright_cyan}{key.rjust(10)}{term.normal}: {text}"
            for key, text in keys
        )

    footer = "\nPress any key to exit."
    print(term.home + term.clear + intro)
    print(render_mapping(BINDINGS))
    print("Mode")
    print(render_mapping(MODES))
    print(footer)
