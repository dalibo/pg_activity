import functools
import inspect
import itertools
from textwrap import TextWrapper, dedent
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Sequence,
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
    Host,
    IOCounter,
    Pct,
    SelectableProcesses,
    ServerInformation,
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


@functools.lru_cache(maxsize=512)
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
    wrapped = term.wrap(text, width=width, max_lines=1)
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
    pg_version: str,
    server_information: ServerInformation,
    system_info: Optional[SystemInfo] = None,
) -> Iterator[str]:
    @functools.singledispatch
    def render(x: Any) -> str:
        if x is None:
            return "-"
        raise AssertionError(f"not implemented for type '{type(x).__name__}'")

    @render.register(str)
    def render_str(s: str) -> str:
        return term.bold_green(s)

    @render.register(int)
    def render_int(n: int) -> str:
        return term.bold_green(str(n))

    @render.register(Pct)
    def render_pct(n: Pct) -> str:
        return term.bold_green(f"{n:.2f}%")

    @render.register(float)
    def render_float(n: float) -> str:
        return term.bold_green(f"{n:.2f}")

    @render.register(IOCounter)
    def render_iocounter(i: IOCounter) -> str:
        hbytes = utils.naturalsize(i.bytes) + "/s"
        counts = str(i.count) + "/s"
        return f"{term.bold_green(hbytes)} - {term.bold_green(counts)}"

    def render_columns(
        columns: Sequence[List[str]], *, delimiter: str
    ) -> Iterator[str]:
        column_widths = [
            max(len(column_row) for column_row in column) for column in columns
        ]

        def indent(text: str) -> str:
            return " " + text

        for row in itertools.zip_longest(*columns, fillvalue=""):
            yield indent(
                "".join(
                    (cell + delimiter).ljust(width + len(delimiter))
                    for width, cell in zip(column_widths, row)
                )
            ).rstrip().rstrip(delimiter.strip())

    si = server_information

    """Return window header lines."""
    pg_host = f"{host.user}@{host.host}:{host.port}/{host.dbname}"
    yield (
        " - ".join(
            [
                pg_version,
                f"{term.bold}{host.hostname}{term.normal}",
                f"{term.cyan}{pg_host}{term.normal}",
                f"Ref.: {term.yellow}{ui.refresh_time}s{term.normal}",
                f"Duration mode: {term.yellow}{ui.duration_mode.name}{term.normal}",
            ]
            + (
                [f"Min. duration: {term.yellow}{ui.min_duration}s{term.normal}"]
                if ui.min_duration
                else []
            )
        )
    )

    total_size = utils.naturalsize(si.total_size)
    size_ev = f"{utils.naturalsize(si.size_evolution)}/s"
    uptime = utils.naturaltimedelta(si.uptime)

    if ui.show_instance_info_in_header:
        # First rows are always displayed, as the underlying data is always available.
        columns = [
            [f"* Global: {render(uptime)} uptime"],
            [f"{render(total_size)} dbs size - {render(size_ev)} growth"],
            [f"{render(si.cache_hit_ratio_last_snap)} cache hit ratio"],
        ]
        yield from render_columns(columns, delimiter=f" {term.bold_blue('⋅')} ")

        columns = [
            [f"  Sessions: {render(si.total)}/{render(si.max_connections)} total"],
            [f"{render(si.active_connections)} active"],
            [f"{render(si.idle)} idle"],
            [f"{render(si.idle_in_transaction)} idle in txn"],
            [f"{render(si.idle_in_transaction_aborted)} idle in txn abrt"],
            [f"{render(si.waiting)} waiting"],
        ]
        yield from render_columns(columns, delimiter=f" {term.bold_blue('⋅')} ")

        if si.temporary_file is not None:
            temp_files = si.temporary_file.temp_files
            temp_size = utils.naturalsize(si.temporary_file.temp_bytes)
        else:
            temp_files = None
            temp_size = None
        columns = [
            [f"  Activity: {render(si.tps)} tps"],
            [f"{render(si.insert_per_second)} insert/s"],
            [f"{render(si.update_per_second)} update/s"],
            [f"{render(si.delete_per_second)} delete/s"],
            [f"{render(si.tuples_returned_per_second)} tuples returned/s"],
            [f"{render(temp_files)} temp files"],
            [f"{render(temp_size)} temp size"],
        ]
        yield from render_columns(columns, delimiter=f" {term.bold_blue('⋅')} ")
    if ui.show_worker_info_in_header:
        columns = [
            [
                f"* Worker processes: {render(si.worker_processes)}/{render(si.max_worker_processes)} total"
            ],
            [
                f"{render(si.logical_replication_workers)}/{render(si.max_logical_replication_workers)} logical workers"
            ],
            [
                f"{render(si.parallel_workers)}/{render(si.max_parallel_workers)} parallel workers"
            ],
        ]
        yield from render_columns(columns, delimiter=f" {term.bold_blue('⋅')} ")

        columns = [
            [
                f"  Other processes & info: {render(si.autovacuum_workers)}/{render(si.autovacuum_max_workers)} autovacuum workers"
            ],
            [f"{render(si.wal_senders)}/{render(si.max_wal_senders)} wal senders"],
            [f"{render(si.wal_receivers)} wal receivers"],
            [
                f"{render(si.replication_slots)}/{render(si.max_replication_slots)} repl. slots"
            ],
        ]
        yield from render_columns(columns, delimiter=f" {term.bold_blue('⋅')} ")

    # System information, only available in "local" mode.
    if system_info is not None and ui.show_system_info_in_header:
        used, bc, free, total = (
            utils.naturalsize(system_info.memory.used),
            utils.naturalsize(system_info.memory.buff_cached),
            utils.naturalsize(system_info.memory.free),
            utils.naturalsize(system_info.memory.total),
        )
        system_columns = [
            [f"* Mem.: {render(total)} total"],
            [f"{render(free)} ({render(system_info.memory.pct_free)}) free"],
            [f"{render(used)} ({render(system_info.memory.pct_used)}) used"],
            [f"{render(bc)} ({render(system_info.memory.pct_bc)}) buff+cached"],
        ]
        yield from render_columns(system_columns, delimiter=f" {term.bold_blue('⋅')} ")

        used, free, total = (
            utils.naturalsize(system_info.swap.used),
            utils.naturalsize(system_info.swap.free),
            utils.naturalsize(system_info.swap.total),
        )
        system_columns = [
            [f"  Swap: {render(total)} total"],
            [f"{render(free)} ({render(system_info.swap.pct_free)}) free"],
            [f"{render(used)} ({render(system_info.swap.pct_used)}) used"],
        ]
        yield from render_columns(system_columns, delimiter=f" {term.bold_blue('⋅')} ")

        iops = f"{system_info.max_iops}/s"
        system_columns = [
            [f"  IO: {render(iops)} max iops"],
            [f"{render(system_info.io_read)} read"],
            [f"{render(system_info.io_write)} write"],
        ]
        yield from render_columns(system_columns, delimiter=f" {term.bold_blue('⋅')} ")

        load = system_info.load
        system_columns = [
            [
                f"  Load average: {render(load.avg1)} {render(load.avg5)} {render(load.avg15)}"
            ],
        ]
        yield from render_columns(system_columns, delimiter=f" {term.bold_blue('⋅')} ")


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
    yield term.ljust(" ".join(htitles), fillchar=" ") + term.normal


def get_indent(ui: UI) -> str:
    """Return indentation for Query column.

    >>> from pgactivity.types import Flag, UI
    >>> ui = UI.make(flag=Flag.CPU)
    >>> get_indent(ui)
    '                         '
    >>> ui = UI.make(flag=Flag.PID | Flag.DATABASE | Flag.APPNAME | Flag.RELATION)
    >>> get_indent(ui)
    '                                                           '
    """
    return " " * sum(c.min_width + 1 for c in ui.columns() if c.name != "Query")


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
    maxlines: int,
    width: Optional[int],
) -> Iterator[str]:
    """Display table rows with processes information."""

    if width is None:
        width = term.width

    def cell(
        value: Any,
        column: Column,
    ) -> None:
        color = getattr(term, colors.FIELD_BY_MODE[column.color(value)][color_type])
        # We also restore 'normal' style so that the next item does not
        # inherit from that of the previous one.
        text.append(f"{color}{column.render(value)}{term.normal}")

    position = processes.position()
    if position is None:
        display_processes = iter(processes)
    else:
        # Scrolling is handled here. We just have to manage the start position of the
        # display. the length is managed by @limit.
        if ui.wrap_query:
            # When the query is wrapped, we always display selected process first (sort
            # of relative scrolling).
            start = position
        else:
            # Otherwise, we compute the start position of the table and try to have a 5 lines
            # leeway at the bottom of the page to increase readability.
            start = 0
            bottom = int(maxlines // 5)
            if position is not None and position >= maxlines - bottom:
                start = position - maxlines + 1 + bottom

        display_processes = itertools.chain(
            iter(processes[-(len(processes) - start) :]), iter(processes[:start])
        )

    focused, pinned = processes.focused, processes.pinned

    for process in display_processes:
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
        qwidth = width - len(indent)

        if qwidth > 0 and process.query is not None:
            query = format_query(process.query, process.is_parallel_worker)

            if not ui.wrap_query:
                query_value = query[:qwidth]
            else:
                wrapped_lines = TextWrapper(qwidth).wrap(query)
                query_value = f"\n{indent}".join(wrapped_lines)

            cell(query_value, ui.column("query"))

        for line in (" ".join(text) + term.normal).splitlines():
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
    pg_version: str,
    server_information: ServerInformation,
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
            pg_version=pg_version,
            server_information=server_information,
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
        maxlines=lines_counter.value,  # Used by process_rows
        lines_counter=lines_counter,  # Used by @limit
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
