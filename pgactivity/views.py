import functools
import itertools
from datetime import timedelta
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
    Union,
)

from blessed import Terminal
from blessed.formatters import FormattingString

from .keys import (
    BINDINGS,
    EXIT_KEY,
    HELP as HELP_KEY,
    KEYS_BY_QUERYMODE,
    Key,
    MODES,
    PAUSE_KEY,
)
from .types import (
    ActivityStats,
    BWProcess,
    Column,
    DBInfo,
    Flag,
    Host,
    IOCounter,
    LocalRunningProcess,
    MemoryInfo,
    QueryDisplayMode,
    QueryMode,
    RunningProcess,
    SystemInfo,
    UI,
)
from . import utils
from .activities import sorted as sorted_processes

LINE_COLORS = {
    "pid": {"default": "cyan", "cursor": "cyan_reverse", "yellow": "yellow_bold"},
    "database": {
        "default": "black_bold",
        "cursor": "cyan_reverse",
        "yellow": "yellow_bold",
    },
    "appname": {
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


line_counter = functools.partial(itertools.count, step=-1)


def limit(func: Callable[..., Iterable[str]]) -> Callable[..., int]:
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
    count(0, -1)
    >>> count = line_counter(3)
    >>> limit(view)(term, 2, lines_counter=count)
    line #0
    line #1
    >>> count
    count(1, -1)
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
    count(9, -1)
    """

    @functools.wraps(func)
    def wrapper(term: Terminal, *args: Any, **kwargs: Any) -> None:
        counter = kwargs.pop("lines_counter", None)
        for line in func(term, *args, **kwargs):
            print(line)
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
    {term.bold_green}pg_activity {version} - {term.link(project_url, project_url)}
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
    tps: int,
    active_connections: int,
    system_info: Optional[SystemInfo] = None,
) -> Iterator[str]:
    """Return window header lines."""
    pg_host = f"{host.user}@{host.host}:{host.port}/{host.dbname}"
    yield (
        " - ".join(
            [
                host.pg_version,
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
        yield term.black_bold_on_orange(term.center("PAUSE", fillchar=" "))
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


def format_duration(duration: Optional[float]) -> Tuple[str, str]:
    """Return a string from 'duration' value along with the color for rendering.

    >>> format_duration(None)
    ('N/A     ', 'time_green')
    >>> format_duration(-0.000062)
    ('0.000000', 'time_green')
    >>> format_duration(0.1)
    ('0.100000', 'time_green')
    >>> format_duration(1.2)
    ('00:01.20', 'time_yellow')
    >>> format_duration(12345)
    ('205:45.00', 'time_red')
    >>> format_duration(60001)
    ('16 h', 'time_red')
    """
    if duration is None:
        return "N/A".ljust(8), "time_green"

    if duration < 1:
        if duration < 0:
            duration = 0
        ctime = f"{duration:.6f}"
        color = "time_green"
    elif duration < 60000:
        if duration < 3:
            color = "time_yellow"
        else:
            color = "time_red"
        duration_d = timedelta(seconds=float(duration))
        mic = "%.6d" % duration_d.microseconds
        ctime = "%s:%s.%s" % (
            str((duration_d.seconds // 60)).zfill(2),
            str((duration_d.seconds % 60)).zfill(2),
            mic[:2],
        )
    else:
        ctime = "%s h" % str(int(duration / 3600))
        color = "time_red"

    return ctime, color


@limit
def processes_rows(
    term: Terminal,
    ui: UI,
    processes: Union[
        Iterable[BWProcess], Iterable[RunningProcess], Iterable[LocalRunningProcess]
    ],
    *,
    color_type: str = "default",
) -> Iterator[str]:
    """Display table rows with processes information."""

    # if color_type == 'default' and self.pid_yank.count(process['pid']) > 0:
    # color_type = 'yellow'

    def color_for(field: str) -> FormattingString:
        return getattr(term, LINE_COLORS[field][color_type])

    def text_append(value: str) -> None:
        # We also restore 'normal' style so that the next item does not
        # inherit previous one's style.
        text.append(value + term.normal)

    def cell(
        value: Any,
        column: Column,
        color_key: str,
    ) -> None:
        text_append(f"{color_for(color_key)}{column.render(value)}")

    flag = ui.flag
    query_mode = ui.query_mode

    for process in processes:
        text: List[str] = []
        if flag & Flag.PID:
            cell(process.pid, ui.column("pid"), "pid")
        if flag & Flag.DATABASE:
            cell(process.database, ui.column("database"), "database")
        if flag & Flag.APPNAME:
            cell(process.appname, ui.column("appname"), "appname")
        if flag & Flag.USER:
            cell(process.user, ui.column("user"), "user")
        if flag & Flag.CLIENT:
            cell(process.client, ui.column("client"), "client")
        if query_mode == QueryMode.activities and isinstance(
            process, LocalRunningProcess
        ):
            if flag & Flag.CPU:
                cell(process.cpu, ui.column("cpu"), "cpu")
            if flag & Flag.MEM:
                cell(process.mem, ui.column("mem"), "mem")
            if flag & Flag.READ:
                cell(process.read, ui.column("read"), "read")
            if flag & Flag.WRITE:
                cell(process.write, ui.column("write"), "write")

        elif query_mode in (QueryMode.waiting, QueryMode.blocking):
            assert isinstance(process, BWProcess), process
            if flag & Flag.RELATION:
                cell(process.relation, ui.column("relation"), "relation")
            if flag & Flag.TYPE:
                cell(process.type, ui.column("type"), "type")

            if flag & Flag.MODE:
                mode = process.mode
                if mode in (
                    "ExclusiveLock",
                    "RowExclusiveLock",
                    "AccessExclusiveLock",
                ):
                    mode_color = "mode_red"
                else:
                    mode_color = "mode_yellow"
                cell(mode, ui.column("mode"), mode_color)

        if flag & Flag.TIME:
            ctime, color = format_duration(process.duration)
            cell(ctime, ui.column("time"), color)

        if query_mode == QueryMode.activities and flag & Flag.WAIT:
            assert isinstance(process, RunningProcess)
            if process.wait:
                wait_value, wait_color = "Y", "wait_red"
            else:
                wait_value, wait_color = "N", "wait_green"
            cell(wait_value, ui.column("wait"), wait_color)

        if (
            isinstance(process, LocalRunningProcess)
            and query_mode == QueryMode.activities
            and flag & Flag.IOWAIT
        ):
            assert process.io_wait in "YN", process.io_wait
            if process.io_wait == "Y":
                iowait_value, iowait_color = "Y", "wait_red"
            else:
                iowait_value, iowait_color = "N", "wait_green"
            cell(iowait_value, ui.column("iowait"), iowait_color)

        state = utils.short_state(process.state)
        if state == "active":
            color_state = "state_green"
        elif state == "idle in trans":
            color_state = "state_yellow"
        elif state == "idle in trans (a)":
            color_state = "state_red"
        else:
            color_state = "state_default"
        cell(state, ui.column("state"), color_state)

        indent = get_indent(ui) + " "
        dif = term.width - len(indent)

        verbose_mode = ui.verbose_mode
        if dif < 0:
            # Switch to wrap_noindent mode if terminal is too narrow.
            verbose_mode = QueryDisplayMode.wrap_noindent

        query = format_query(process.query, process.is_parallel_worker)

        if verbose_mode == QueryDisplayMode.truncate:
            text_append(" " + f"{color_for('query')}{query[:dif]}")
        else:
            query_r = f"{color_for('query')}{query}"
            if verbose_mode == QueryDisplayMode.wrap_noindent:
                if term.length(query_r.split(" ", 1)[0]) >= dif:
                    # Query too long to even start on the first line, wrap all
                    # lines.
                    query_lines = term.wrap(query_r, width=term.width)
                else:
                    # Only wrap subsequent lines.
                    wrapped_lines = term.wrap(query_r, width=dif)
                    query_lines = [" " + wrapped_lines[0]] + term.wrap(
                        " ".join(wrapped_lines[1:]), width=term.width
                    )
                text_append("\n".join(query_lines))
            else:
                assert (
                    verbose_mode == QueryDisplayMode.wrap
                ), f"unexpected mode {verbose_mode}"
                wrapped_lines = term.wrap(" " + query_r, width=dif)
                text_append(f"\n{indent}".join(wrapped_lines))

        for line in ("".join(text) + term.normal).splitlines():
            yield line


def footer(term: Terminal) -> None:
    """Display footer line."""
    query_modes_help = [
        ("/".join(keys[:-1]), qm.value) for qm, keys in KEYS_BY_QUERYMODE.items()
    ]
    assert PAUSE_KEY.name is not None
    footer_values = query_modes_help + [
        (PAUSE_KEY.name, PAUSE_KEY.description),
        (EXIT_KEY.value, EXIT_KEY.description),
        (HELP_KEY, "help"),
    ]
    width = max(len(desc) for _, desc in footer_values)
    print(
        term.ljust(
            " ".join(
                [
                    f"{key} {term.cyan_reverse(term.ljust(desc.capitalize(), width=width, fillchar=' '))}"
                    for key, desc in footer_values
                ]
            ),
            fillchar=" ",
        )
        + term.normal,
        end="",
    )


def screen(
    term: Terminal,
    ui: UI,
    *,
    host: Host,
    dbinfo: DBInfo,
    tps: int,
    active_connections: int,
    activity_stats: ActivityStats,
    render_footer: bool = True,
) -> None:
    """Display the screen."""

    processes: Union[List[RunningProcess], List[BWProcess], List[LocalRunningProcess]]
    system_info: Optional[SystemInfo]
    if isinstance(activity_stats, tuple):
        processes, system_info = activity_stats
    else:
        processes, system_info = activity_stats, None
    processes = sorted_processes(processes, key=ui.sort_key, reverse=True)  # type: ignore  # TODO: fixme

    print(term.clear + term.home, end="")
    top_height = term.height - 1
    lines_counter = line_counter(top_height)
    header(
        term,
        ui,
        host=host,
        dbinfo=dbinfo,
        tps=tps,
        active_connections=active_connections,
        system_info=system_info,
        lines_counter=lines_counter,
    )

    query_mode(term, ui, lines_counter=lines_counter)
    columns_header(term, ui, lines_counter=lines_counter)
    processes_rows(
        term,
        ui,
        processes,
        lines_counter=lines_counter,
    )
    if render_footer:
        with term.location(x=0, y=top_height):
            footer(term)
