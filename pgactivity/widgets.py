from blessed import Terminal


def boxed(
    term: Terminal, content: str, *, border_color: str = "white", center: bool = False
) -> str:
    border_width = term.length(content) + 2
    border_formatter = term.formatter(border_color)
    lines = [
        border_formatter("┌" + "─" * border_width + "┐"),
        " ".join([border_formatter("│") + term.normal, content, border_formatter("│")]),
        border_formatter("└" + "─" * border_width + "┘") + term.normal,
    ]
    if center:
        lines = [term.center(line) for line in lines]
    return "\n".join(lines)
