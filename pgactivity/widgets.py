from typing import Optional

from blessed import Terminal


def boxed(
    term: Terminal,
    content: str,
    *,
    border: bool = True,
    border_color: str = "white",
    center: bool = False,
    width: Optional[int] = None,
) -> str:
    if border:
        border_width = term.length(content) + 2
        border_formatter = getattr(term, border_color)
        lines = [
            border_formatter("┌" + "─" * border_width + "┐"),
            " ".join(
                [border_formatter("│") + term.normal, content, border_formatter("│")]
            ),
            border_formatter("└" + "─" * border_width + "┘") + term.normal,
        ]
    else:
        # border is disabled in UI tests.
        lines = ["", content, ""]
    if center:
        if width is None:
            width = term.width
        lines = [term.center(line, width=width) for line in lines]
    return "\n".join(lines)
