import functools
import inspect
from textwrap import dedent
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    List,
    NoReturn,
    Optional,
    Tuple,
)

from blessed import Terminal

from .compat import link
from .keys import (
    BINDINGS,
    EXIT_KEY,
    HELP as HELP_KEY,
    KEYS_BY_QUERYMODE,
    Key,
    MODES,
    PAUSE_KEY,
    PROCESS_CANCEL,
    PROCESS_KILL,
    PROCESS_PIN,
)
from .types import (
    ActivityStats,
    Column,
    DBInfo,
    Host,
    IOCounter,
    MemoryInfo,
    QueryDisplayMode,
    SelectableProcesses,
    SystemInfo,
    UI,
)
from . import colors, utils
from .activities import sorted as sorted_processes


class line_counter:
    def __init__(self, start: int) -> None:
        self.value = start

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value})"

    def __next__(self) -> int:
        current_value = self.value
        self.value -= 1
        return current_value


def shorten(term: Terminal, text: str, width: Optional[int] = None) -> str:
    r"""Truncate 'text' to fit in the given 'width' (or term.width).

    This is similar to textwrap.shorten() but sequence-aware.

    >>> term = Terminal()
    >>> text = f"{term.green('hello')}, world"
    >>> text
    'hello, world'
    >>> shorten(term, text, 6)
    'hello,'
    >>> shorten(term, text, 3)
    'hel'
    >>> shorten(term, "", 3)
    ''
    """
    if not text:
        return ""
    wrapped: List[str] = term.wrap(text, width=width, max_lines=1)
    return wrapped[0] + term.normal


def limit(func: Callable[..., Iterable[str]]) -> Callable[..., None]:
    """View decorator handling screen height limit.

    >>> term = Terminal()

    >>> def view(term, n, *, prefix="line"):
    ...     for i in range(n):
    ...         yield f"{prefix} #{i}"

    >>> count = line_counter(2)
    >>> limit(view)(term, 3, lines_counter=count)
    line #0
    line #1
    >>> count
    line_counter(0)
    >>> count = line_counter(3)
    >>> limit(view)(term, 2, lines_counter=count)
    line #0
    line #1
    >>> count
    line_counter(1)
    >>> limit(view)(term, 3, prefix="row")
    row #0
    row #1
    row #2

    A single line is displayed with an EOL as well:
    >>> count = line_counter(10)
    >>> limit(view)(term, 1, lines_counter=count) or print("<--", end="")
    line #0
    <--
    >>> count
    line_counter(9)
    """

    @functools.wraps(func)
    def wrapper(term: Terminal, *args: Any, **kwargs: Any) -> None:
        counter = kwargs.pop("lines_counter", None)
        width = kwargs.pop("width", None)
        signature = inspect.signature(func)
        if "width" in signature.parameters:
            kwargs["width"] = width
        for line in func(term, *args, **kwargs):
            print(shorten(term, line, width) + term.clear_eol)
            if counter is not None and next(counter) == 1:
                break

    return wrapper


@functools.singledispatch
def render(x: NoReturn, column_width: int) -> str:
    raise AssertionError(f"not implemented for type '{type(x).__name__}'")


@render.register(MemoryInfo)
def render_meminfo(m: MemoryInfo, column_width: int) -> str:
    used, total = utils.naturalsize(m.used), utils.naturalsize(m.total)
    return _columns(f"{m.percent}%", f"{used}/{total}", column_width)


@render.register(IOCounter)
def render_iocounter(i: IOCounter, column_width: int) -> str:
    hbytes = utils.naturalsize(i.bytes)
    return _columns(f"{hbytes}/s", f"{i.count}/s", column_width)


def _columns(left: str, right: str, total_width: int) -> str:
    column_width, r = divmod(total_width, 2)
    if r:
        column_width -= 1
    return " - ".join([left.rjust(column_width - 1), right.ljust(column_width - 1)])


@limit
def help(term: Terminal, version: str, is_local: bool) -> Iterable[str]:
    """Render help menu."""
    project_url = "https://github.com/dalibo/pg_activity"
    intro = dedent(
        f"""\
    {term.bold_green}pg_activity {version} - {link(term, project_url, project_url)}
    {term.normal}Released under PostgreSQL License.
    """
    )

    def key_mappings(keys: Iterable[Key]) -> Iterable[str]:
        for key in keys:
            key_name = key.name or key.value
            yield f"{term.bright_cyan}{key_name.rjust(10)}{term.normal}: {key.description}"

    footer = "Press any key to exit."
    for line in intro.splitlines():
        yield line
    yield ""

    bindings = BINDINGS
    if not is_local:
        bindings = [b for b in bindings if not b.local_only]
    yield from key_mappings(bindings)
    yield "Mode"
    yield from key_mappings(MODES)
    yield ""
    yield footer


@limit
def header(
    term: Terminal,
    ui: UI,
    *,
    host: Host,
    dbinfo: DBInfo,
    pg_version: str,
    tps: int,
    active_connections: int,
    system_info: Optional[SystemInfo] = None,
) -> Iterator[str]:
    """Return window header lines."""
    pg_host = f"{host.user}@{host.host}:{host.port}/{host.dbname}"
    yield (
        " - ".join(
            [
                pg_version,
                f"{term.bold}{host.hostname}{term.normal}",
                f"{term.cyan}{pg_host}{term.normal}",
                f"Ref.: {ui.refresh_time}s",
            ]
            + ([f"Min. duration: {ui.min_duration}s"] if ui.min_duration else [])
        )
    )

    def row(*columns: Tuple[str, str, int]) -> str:
        return " | ".join(
            f"{title}: {value.center(width)}" for title, value, width in columns
        ).rstrip()

    def indent(text: str, indent: int = 1) -> str:
        return " " * indent + text

    col_width = 30  # TODO: use screen size

    total_size = utils.naturalsize(dbinfo.total_size)
    size_ev = utils.naturalsize(dbinfo.size_ev)
    yield indent(
        row(
            (
                "Size",
                _columns(total_size, f"{size_ev}/s", 20),
                col_width,
            ),
            ("TPS", f"{term.bold_green}{str(tps).rjust(11)}{term.normal}", 20),
            (
                "Active connections",
                f"{term.bold_green}{str(active_connections).rjust(11)}{term.normal}",
                20,
            ),
            (
                "Duration mode",
                f"{term.bold_green}{ui.duration_mode.name.rjust(11)}{term.normal}",
                5,
            ),
        )
    )

    if system_info is not None:
        yield indent(
            row(
                ("Mem.", render(system_info.memory, col_width // 2), col_width),
                ("IO Max", f"{system_info.max_iops:8}/s", col_width // 4),
            )
        )
        yield indent(
            row(
                ("Swap", render(system_info.swap, col_width // 2), col_width),
                (
                    "Read",
                    render(system_info.io_read, col_width // 2 - len("Read")),
                    col_width,
                ),
            )
        )
        load = system_info.load
        yield indent(
            row(
                (
                    "Load",
                    f"{load.avg1:.2f} {load.avg5:.2f} {load.avg15:.2f}",
                    col_width,
                ),
                (
                    "Write",
                    render(system_info.io_write, col_width // 2 - len("Write")),
                    col_width,
                ),
            )
        )


@limit
def query_mode(term: Terminal, ui: UI) -> Iterator[str]:
    r"""Display query mode title.

    >>> from pgactivity.types import QueryMode, UI

    >>> term = Terminal()
    >>> ui = UI.make(query_mode=QueryMode.blocking)
    >>> query_mode(term, ui)
                                    BLOCKING QUERIES
    >>> ui = UI.make(query_mode=QueryMode.activities, in_pause=True)
    >>> query_mode(term, ui)  # doctest: +NORMALIZE_WHITESPACE
                                    PAUSE
    """
    if ui.in_pause:
        yield term.black_on_yellow(term.center("PAUSE", fillchar=" "))
    else:
        yield term.green_bold(
            term.center(ui.query_mode.value.upper(), fillchar=" ").rstrip()
        )


@limit
def columns_header(term: Terminal, ui: UI) -> Iterator[str]:
    """Yield columns header lines."""
    htitles = []
    for column in ui.columns():
        color = getattr(term, f"black_on_{column.title_color(ui.sort_key)}")
        htitles.append(f"{color}{column.title_render()}")
    yield term.ljust("".join(htitles), fillchar=" ") + term.normal


def get_indent(ui: UI) -> str:
    """Return identation for Query column.

    >>> from pgactivity.types import Flag, UI
    >>> ui = UI.make(flag=Flag.CPU)
    >>> get_indent(ui)
    '                           '
    >>> ui = UI.make(flag=Flag.PID | Flag.DATABASE | Flag.APPNAME | Flag.RELATION)
    >>> get_indent(ui)
    '                                                             '
    """
    indent = ""
    for column in ui.columns():
        if column.name != "Query":
            indent += column.template_h % " "
    return indent


def format_query(query: str, is_parallel_worker: bool) -> str:
    r"""Return the query string formatted.

    >>> print(format_query("SELECT 1", True))
    \_ SELECT 1
    >>> format_query("SELECT   1", False)
    'SELECT 1'
    """
    prefix = r"\_ " if is_parallel_worker else ""
    return prefix + utils.clean_str(query)


@limit
def processes_rows(
    term: Terminal,
    ui: UI,
    processes: SelectableProcesses,
    width: Optional[int],
) -> Iterator[str]:
    """Display table rows with processes information."""

    if width is None:
        width = term.width

    def text_append(value: str) -> None:
        # We also restore 'normal' style so that the next item does not
        # inherit previous one's style.
        text.append(value + term.normal)

    def cell(
        value: Any,
        column: Column,
    ) -> None:
        color = getattr(term, colors.FIELD_BY_MODE[column.color(value)][color_type])
        text_append(f"{color}{column.render(value)}")

    focused, pinned = processes.focused, processes.pinned

    for process in processes:
        if process.pid == focused:
            color_type = "cursor"
        elif process.pid in pinned:
            color_type = "yellow"
        else:
            color_type = "default"
        text: List[str] = []
        for column in ui.columns():
            field = column.key
            if field != "query":
                cell(getattr(process, field), column)

        indent = get_indent(ui) + " "
        dif = width - len(indent)

        verbose_mode = ui.verbose_mode
        if dif < 0:
            # Switch to wrap_noindent mode if terminal is too narrow.
            verbose_mode = QueryDisplayMode.wrap_noindent

        if process.query is not None:
            query = format_query(process.query, process.is_parallel_worker)

            if verbose_mode == QueryDisplayMode.truncate:
                query_value = query[:dif]
            else:
                if verbose_mode == QueryDisplayMode.wrap_noindent:
                    if term.length(query.split(" ", 1)[0]) >= dif:
                        # Query too long to even start on the first line, wrap all
                        # lines.
                        query_lines = term.wrap(query, width=width)
                    else:
                        # Only wrap subsequent lines.
                        wrapped_lines = term.wrap(query, width=dif)
                        if wrapped_lines:
                            query_lines = [wrapped_lines[0]] + term.wrap(
                                " ".join(wrapped_lines[1:]), width=width
                            )
                        else:
                            query_lines = []
                    query_value = "\n".join(query_lines)
                else:
                    assert (
                        verbose_mode == QueryDisplayMode.wrap
                    ), f"unexpected mode {verbose_mode}"
                    wrapped_lines = term.wrap(query, width=dif)
                    query_value = f"\n{indent}".join(wrapped_lines)

            cell(query_value, ui.column("query"))

        for line in ("".join(text) + term.normal).splitlines():
            yield line


def footer_message(term: Terminal, message: str, width: Optional[int] = None) -> None:
    if width is None:
        width = term.width
    print(term.center(message[:width]) + term.normal, end="")


def footer_help(term: Terminal, width: Optional[int] = None) -> None:
    """Footer line with help keys."""
    query_modes_help = [
        ("/".join(keys[:-1]), qm.value) for qm, keys in KEYS_BY_QUERYMODE.items()
    ]
    assert PAUSE_KEY.name is not None
    footer_values = query_modes_help + [
        (PAUSE_KEY.name, PAUSE_KEY.description),
        (EXIT_KEY.value, EXIT_KEY.description),
        (HELP_KEY, "help"),
    ]
    render_footer(term, footer_values, width)


def render_footer(
    term: Terminal, footer_values: List[Tuple[str, str]], width: Optional[int]
) -> None:
    if width is None:
        width = term.width
    ncols = len(footer_values)
    column_width = (width - ncols - 1) // ncols

    def render_column(key: str, desc: str) -> str:
        col_width = column_width - term.length(key) - 1
        if col_width <= 0:
            return ""
        desc = term.ljust(desc[:col_width], width=col_width, fillchar=" ")
        return f"{key} {term.cyan_reverse(desc)}"

    row = " ".join(
        [render_column(key, desc.capitalize()) for key, desc in footer_values]
    )
    assert term.length(row) <= width, (term.length(row), width, ncols)
    print(term.ljust(row, width=width, fillchar=term.cyan_reverse(" ")), end="")


def footer_interative_help(term: Terminal, width: Optional[int] = None) -> None:
    """Footer line with help keys for interactive mode."""
    assert PROCESS_PIN.name is not None
    footer_values = [
        (PROCESS_CANCEL, "cancel current query"),
        (PROCESS_KILL, "terminate current query"),
        (PROCESS_PIN.name, PROCESS_PIN.description),
        ("Other", "back to activities"),
        (EXIT_KEY.value, EXIT_KEY.description),
    ]
    return render_footer(term, footer_values, width)


def screen(
    term: Terminal,
    ui: UI,
    *,
    host: Host,
    dbinfo: DBInfo,
    pg_version: str,
    tps: int,
    active_connections: int,
    activity_stats: ActivityStats,
    message: Optional[str],
    render_header: bool = True,
    render_footer: bool = True,
    width: Optional[int] = None,
) -> None:
    """Display the screen."""

    system_info: Optional[SystemInfo]
    if isinstance(activity_stats, tuple):
        processes, system_info = activity_stats
    else:
        processes, system_info = activity_stats, None
    processes.set_items(sorted_processes(processes, key=ui.sort_key, reverse=True))

    print(term.home, end="")
    top_height = term.height - (1 if render_footer else 0)
    lines_counter = line_counter(top_height)

    if render_header:
        header(
            term,
            ui,
            host=host,
            dbinfo=dbinfo,
            pg_version=pg_version,
            tps=tps,
            active_connections=active_connections,
            system_info=system_info,
            lines_counter=lines_counter,
            width=width,
        )

    query_mode(term, ui, lines_counter=lines_counter, width=width)
    columns_header(term, ui, lines_counter=lines_counter, width=width)
    processes_rows(
        term,
        ui,
        processes,
        lines_counter=lines_counter,
        width=width,
    )

    # Clear remaining lines in screen until footer (or EOS)
    print(f"{term.clear_eol}\n" * lines_counter.value, end="")

    if render_footer:
        with term.location(x=0, y=top_height):
            if message is not None:
                footer_message(term, message, width)
            elif ui.interactive():
                footer_interative_help(term, width)
            else:
                footer_help(term, width)
