import enum
import functools
import itertools
from datetime import timedelta
from textwrap import dedent
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple, Union

import humanize
from blessed import Terminal
from blessed.formatters import FormattingString

from .keys import BINDINGS, Key, MODES
from .types import (
    Activity,
    ActivityBW,
    ActivityProcess,
    ColumnTitle,
    DBInfo,
    DurationMode,
    Flag,
    Host,
    MemoryInfo,
    QueryDisplayMode,
    QueryMode,
    SortKey,
    SystemInfo,
)
from . import utils

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


# Maximum number of columns
MAX_NCOL = 15


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


@limit
def help(term: Terminal, version: str, is_local: bool) -> Iterable[str]:
    """Render help menu.

    >>> term = Terminal()
    >>> help(term, "2.1", True)
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
             c: sort by CPU% desc. (activities)
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
    >>> help(term, "5.0", False)
    pg_activity 5.0 - https://github.com/dalibo/pg_activity
    Released under PostgreSQL License.
    <BLANKLINE>
       Up/Down: scroll process list
             C: activate/deactivate colors
         Space: pause
             v: change display mode
             q: quit
             +: increase refresh time (max:5s)
             -: decrease refresh time (min:0.5s)
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
    host: Host,
    dbinfo: DBInfo,
    tps: int,
    active_connections: int,
    duration_mode: DurationMode,
    refresh_time: float,
    *,
    min_duration: float = 0,
    max_iops: int = 0,
    system_info: Optional[SystemInfo] = None,
) -> Iterator[str]:
    r"""Return window header lines.

    >>> from pgactivity.types import IOCounters, LoadAverage
    >>> term = Terminal()

    Remote host:

    >>> host = Host("PostgreSQL 9.6", "server", "pgadm", "server.prod.tld", 5433, "app")
    >>> dbinfo = DBInfo(10203040506070809, 9999)

    >>> header(term, host, dbinfo, 12, 0, DurationMode.backend, refresh_time=10)
    PostgreSQL 9.6 - server - pgadm@server.prod.tld:5433/app - Ref.: 10s
     Size:      10.2 PB -   10.0 kB/s     | TPS:              12      | Active connections:               0      | Duration mode:     backend

    Local host, with priviledged access:

    >>> host = Host("PostgreSQL 13.1", "localhost", "tester", "host", 5432, "postgres")
    >>> dbinfo = DBInfo(123456789, 12)
    >>> vmem = MemoryInfo(total=6175825920, percent=42.5, used=2007146496)
    >>> swap = MemoryInfo(total=6312423424, used=2340, percent=0.0)
    >>> ios = IOCounters(read_bytes=128, write_bytes=8, read_count=6, write_count=9)
    >>> load = LoadAverage(0.25, 0.19, 0.39)
    >>> sysinfo = SystemInfo(vmem, swap, load, ios)

    >>> header(term, host, dbinfo, 1, 79, DurationMode.query, refresh_time=2,
    ...        min_duration=1.2, max_iops=12, system_info=sysinfo)
    PostgreSQL 13.1 - localhost - tester@host:5432/postgres - Ref.: 2s - Min. duration: 1.2s
     Size:     123.5 MB -  12 Bytes/s     | TPS:               1      | Active connections:              79      | Duration mode:       query
     Mem.:     42.5% -    2.0 GB/6.2 GB   | IO Max:                 12/s
     Swap:      0.0% -    2.3 kB/6.3 GB   | Read:     128 Bytes/s -      6/s
     Load:         0.25 0.19 0.39         | Write:       8 Bytes/s -      9/s
    """
    pg_host = f"{host.user}@{host.host}:{host.port}/{host.dbname}"
    yield (
        " - ".join(
            [
                host.pg_version,
                f"{term.bold}{host.hostname}{term.normal}",
                f"{term.cyan}{pg_host}{term.normal}",
                f"Ref.: {refresh_time}s",
            ]
            + ([f"Min. duration: {min_duration}s"] if min_duration else [])
        )
    )

    def row(*columns: Tuple[str, str, int]) -> str:
        return " | ".join(
            f"{title}: {value.center(width)}" for title, value, width in columns
        ).rstrip()

    def indent(text: str, indent: int = 1) -> str:
        return " " * indent + text

    total_size = humanize.naturalsize(dbinfo.total_size)
    size_ev = humanize.naturalsize(dbinfo.size_ev)
    yield indent(
        row(
            ("Size", f"{total_size.rjust(8)} - {size_ev.rjust(9)}/s", 30),
            ("TPS", f"{term.bold_green}{str(tps).rjust(11)}{term.normal}", 20),
            (
                "Active connections",
                f"{term.bold_green}{str(active_connections).rjust(11)}{term.normal}",
                20,
            ),
            (
                "Duration mode",
                f"{term.bold_green}{duration_mode.name.rjust(11)}{term.normal}",
                5,
            ),
        )
    )

    def render_meminfo(m: MemoryInfo) -> str:
        used, total = humanize.naturalsize(m.used), humanize.naturalsize(m.total)
        return f"{m.percent:6}% - {used.rjust(9)}/{total}"

    def render_ios(nbytes: int, count: int) -> str:
        hbytes = humanize.naturalsize(nbytes)
        return f"{hbytes.rjust(10)}/s - {count:6}/s"

    if system_info is not None:
        col_width = 30  # TODO: use screen size
        yield indent(
            row(
                ("Mem.", render_meminfo(system_info.memory), col_width),
                ("IO Max", f"{max_iops:8}/s", col_width),
            )
        )
        yield indent(
            row(
                ("Swap", render_meminfo(system_info.swap), col_width),
                (
                    "Read",
                    render_ios(system_info.ios.read_bytes, system_info.ios.read_count),
                    col_width,
                ),
            )
        )
        load = system_info.load
        yield indent(
            row(
                ("Load", f"{load.avg1:.2} {load.avg5:.2} {load.avg15:.2}", col_width),
                (
                    "Write",
                    render_ios(
                        system_info.ios.write_bytes, system_info.ios.write_count
                    ),
                    col_width,
                ),
            )
        )


@limit
def query_mode(
    term: Terminal, mode: QueryMode, *, in_pause: bool = False
) -> Iterator[str]:
    r"""Display query mode title.

    >>> from pgactivity.types import QueryMode

    >>> term = Terminal()
    >>> query_mode(term, QueryMode.blocking)  # doctest: +NORMALIZE_WHITESPACE
                                    BLOCKING QUERIES
    >>> query_mode(term, QueryMode.activities, in_pause=True)  # doctest: +NORMALIZE_WHITESPACE
                                    PAUSE
    """
    if in_pause:
        yield term.black_bold_on_orange(term.center("PAUSE", fillchar=" "))
    else:
        yield term.center(term.green_bold(mode.value.upper()))


class Column(enum.Enum):
    """Model for each column that may appear in the table."""

    appname = ColumnTitle(
        name="APP",
        template_h="%16s ",
        flag=Flag.APPNAME,
        mandatory=False,
        sort_key=None,
    )
    client = ColumnTitle(
        name="CLIENT",
        template_h="%16s ",
        flag=Flag.CLIENT,
        mandatory=False,
        sort_key=None,
    )
    cpu = ColumnTitle(
        name="CPU%",
        template_h="%6s ",
        flag=Flag.CPU,
        mandatory=False,
        sort_key=SortKey.cpu,
    )
    database = ColumnTitle(
        name="DATABASE",
        template_h="%-16s ",
        flag=Flag.DATABASE,
        mandatory=False,
        sort_key=None,
    )
    iowait = ColumnTitle(
        name="IOW", template_h="%4s ", flag=Flag.IOWAIT, mandatory=False, sort_key=None
    )
    mem = ColumnTitle(
        name="MEM%",
        template_h="%4s ",
        flag=Flag.MEM,
        mandatory=False,
        sort_key=SortKey.mem,
    )
    mode = ColumnTitle(
        name="MODE", template_h="%16s ", flag=Flag.MODE, mandatory=False, sort_key=None
    )
    pid = ColumnTitle(
        name="PID", template_h="%-6s ", flag=None, mandatory=True, sort_key=None
    )
    query = ColumnTitle(
        name="Query", template_h=" %2s", flag=None, mandatory=True, sort_key=None
    )
    read = ColumnTitle(
        name="READ/s",
        template_h="%8s ",
        flag=Flag.READ,
        mandatory=False,
        sort_key=SortKey.read,
    )
    relation = ColumnTitle(
        name="RELATION",
        template_h="%9s ",
        flag=Flag.RELATION,
        mandatory=False,
        sort_key=None,
    )
    state = ColumnTitle(
        name="state", template_h=" %17s  ", flag=None, mandatory=True, sort_key=None
    )
    time = ColumnTitle(
        name="TIME+",
        template_h="%9s ",
        flag=Flag.TIME,
        mandatory=False,
        sort_key=SortKey.duration,
    )
    type = ColumnTitle(
        name="TYPE", template_h="%16s ", flag=Flag.TYPE, mandatory=False, sort_key=None
    )
    user = ColumnTitle(
        name="USER", template_h="%16s ", flag=Flag.USER, mandatory=False, sort_key=None
    )
    wait = ColumnTitle(
        name="W", template_h="%2s ", flag=Flag.WAIT, mandatory=False, sort_key=None
    )
    write = ColumnTitle(
        name="WRITE/s",
        template_h="%8s ",
        flag=Flag.WRITE,
        mandatory=False,
        sort_key=SortKey.write,
    )


COLUMNS_BY_QUERYMODE: Dict[QueryMode, List[Column]] = {
    QueryMode.activities: [
        Column.pid,
        Column.database,
        Column.appname,
        Column.user,
        Column.client,
        Column.cpu,
        Column.mem,
        Column.read,
        Column.write,
        Column.time,
        Column.wait,
        Column.iowait,
        Column.state,
        Column.query,
    ],
    QueryMode.waiting: [
        Column.pid,
        Column.database,
        Column.appname,
        Column.relation,
        Column.type,
        Column.mode,
        Column.time,
        Column.state,
        Column.query,
    ],
    QueryMode.blocking: [
        Column.pid,
        Column.database,
        Column.appname,
        Column.relation,
        Column.type,
        Column.mode,
        Column.time,
        Column.state,
        Column.query,
    ],
}


@limit
def columns_header(
    term: Terminal, mode: QueryMode, flag: Flag, sort_by: SortKey
) -> Iterator[str]:
    r"""Yield columns header lines.

    >>> term = Terminal()
    >>> columns_header(term, QueryMode.activities, Flag.DATABASE, SortKey.cpu)  # doctest: +NORMALIZE_WHITESPACE
    PID    DATABASE                      state   Query
    >>> columns_header(term, QueryMode.activities, Flag.CPU, SortKey.cpu)  # doctest: +NORMALIZE_WHITESPACE
    PID      CPU%              state   Query
    >>> columns_header(term, QueryMode.activities, Flag.MEM, SortKey.cpu)  # doctest: +NORMALIZE_WHITESPACE
    PID    MEM%              state   Query
    >>> flag = Flag.DATABASE | Flag.APPNAME | Flag.RELATION | Flag.CLIENT | Flag.WAIT
    >>> columns_header(term, QueryMode.blocking, flag, SortKey.duration)  # doctest: +NORMALIZE_WHITESPACE
    PID    DATABASE                      APP  RELATION              state   Query
    >>> columns_header(term, QueryMode.activities, flag, SortKey.duration)  # doctest: +NORMALIZE_WHITESPACE
    PID    DATABASE                      APP           CLIENT  W              state   Query
    """
    columns = (c.value for c in COLUMNS_BY_QUERYMODE[mode])
    htitles = []
    for column in columns:
        if column.mandatory or (column.flag & flag):
            color = getattr(term, f"black_on_{column.color(sort_by)}")
            htitles.append(f"{color}{column.render()}")
    yield term.ljust("".join(htitles), fillchar=" ") + term.normal


def get_indent(mode: QueryMode, flag: Flag, max_ncol: int = MAX_NCOL) -> str:
    """Return identation for Query column.

    >>> get_indent(QueryMode.activities, Flag.CPU)
    '                                  '
    >>> flag = Flag.DATABASE | Flag.APPNAME | Flag.RELATION
    >>> get_indent(QueryMode.activities, flag)
    '                                                             '
    """
    indent = ""
    columns = (c.value for c in COLUMNS_BY_QUERYMODE[mode])
    for idx, column in enumerate(columns):
        if column.mandatory or column.flag & flag:
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
    processes: Union[Iterable[Activity], Iterable[ActivityProcess]],
    *,
    is_local: bool,
    flag: Flag,
    query_mode: QueryMode,
    color_type: str = "default",
    verbose_mode: QueryDisplayMode = QueryDisplayMode.default(),
) -> Iterator[str]:
    r"""Display table rows with processes information.

    >>> term = Terminal(force_styling=None)
    >>> processes = [
    ...     ActivityProcess(
    ...         pid="6239",
    ...         appname="pgbench",
    ...         database="pgbench",
    ...         user="postgres",
    ...         client="local",
    ...         cpu=0.1,
    ...         mem=0.993_254_939_413_836,
    ...         read=7,
    ...         write=12.3,
    ...         state="idle in transaction",
    ...         query="UPDATE pgbench_accounts SET abalance = abalance + 141 WHERE aid = 1932841;",
    ...         duration=None,
    ...         wait=False,
    ...         io_wait="N",
    ...         is_parallel_worker=False,
    ...     ),
    ...     ActivityProcess(
    ...         pid="6228",
    ...         appname="pgbench",
    ...         database="pgbench",
    ...         user="postgres",
    ...         client="local",
    ...         cpu=0.2,
    ...         mem=1.024_758_418_061_11,
    ...         read=0.2,
    ...         write=1_128_201,
    ...         state="active",
    ...         query="UPDATE pgbench_accounts SET abalance = abalance + 3062 WHERE aid = 7289374;",
    ...         duration=0.000413,
    ...         wait=False,
    ...         io_wait="Y",
    ...         is_parallel_worker=True,
    ...     ),
    ...     ActivityProcess(
    ...         pid="1234",
    ...         appname="accounting",
    ...         database="business",
    ...         user="bob",
    ...         client="local",
    ...         cpu=2.4,
    ...         mem=1.031_191_760_016_45,
    ...         read=9_876_543.21,
    ...         write=1_234,
    ...         state="active",
    ...         query="SELECT product_id, p.name FROM products p LEFT JOIN sales s USING (product_id) WHERE s.date > CURRENT_DATE - INTERVAL '4 weeks' GROUP BY product_id, p.name, p.price, p.cost HAVING sum(p.price * s.units) > 5000;",
    ...         duration=1234,
    ...         wait=True,
    ...         io_wait="N",
    ...         is_parallel_worker=False,
    ...     ),
    ... ]

    >>> flag = Flag.CPU|Flag.MEM|Flag.DATABASE
    >>> term.width
    80

    >>> processes_rows(term, processes, is_local=True, flag=flag,
    ...                query_mode=QueryMode.activities)
    6239   pgbench             0.1  1.0      idle in trans   UPDATE pgbench_accounts
    SET abalance = abalance + 141 WHERE aid = 1932841;
    6228   pgbench             0.2  1.0             active   \_ UPDATE
    pgbench_accounts SET abalance = abalance + 3062 WHERE aid = 7289374;
    1234   business            2.4  1.0             active   SELECT product_id,
    p.name FROM products p LEFT JOIN sales s USING (product_id) WHERE s.date >
    CURRENT_DATE - INTERVAL '4 weeks' GROUP BY product_id, p.name, p.price, p.cost
    HAVING sum(p.price * s.units) > 5000;

    >>> processes_rows(term, processes, is_local=True, flag=flag,
    ...                query_mode=QueryMode.activities,
    ...                verbose_mode=QueryDisplayMode.truncate)
    6239   pgbench             0.1  1.0      idle in trans   UPDATE pgbench_accounts
    6228   pgbench             0.2  1.0             active   \_ UPDATE pgbench_accou
    1234   business            2.4  1.0             active   SELECT product_id, p.na

    >>> processes_rows(term, processes, is_local=True, flag=flag,
    ...                query_mode=QueryMode.activities,
    ...                verbose_mode=QueryDisplayMode.wrap)
    6239   pgbench             0.1  1.0      idle in trans   UPDATE
                                                             pgbench_accounts SET
                                                             abalance = abalance +
                                                             141 WHERE aid =
                                                             1932841;
    6228   pgbench             0.2  1.0             active   \_ UPDATE
                                                             pgbench_accounts SET
                                                             abalance = abalance +
                                                             3062 WHERE aid =
                                                             7289374;
    1234   business            2.4  1.0             active   SELECT product_id,
                                                             p.name FROM products p
                                                             LEFT JOIN sales s USING
                                                             (product_id) WHERE
                                                             s.date > CURRENT_DATE -
                                                             INTERVAL '4 weeks'
                                                             GROUP BY product_id,
                                                             p.name, p.price, p.cost
                                                             HAVING sum(p.price *
                                                             s.units) > 5000;

    >>> allflags = Flag.IOWAIT|Flag.MODE|Flag.TYPE|Flag.RELATION|Flag.WAIT|Flag.TIME|Flag.WRITE|Flag.READ|Flag.MEM|Flag.CPU|Flag.USER|Flag.CLIENT|Flag.APPNAME|Flag.DATABASE
    >>> term.width
    80

    # terminal is too narrow given selected flags, we switch to wrap_noindent mode
    >>> processes_rows(term, processes, is_local=True, flag=allflags,
    ...                query_mode=QueryMode.activities,
    ...                verbose_mode=QueryDisplayMode.wrap)  # doctest: +NORMALIZE_WHITESPACE
    6239   pgbench                   pgbench         postgres            local    0.1  1.0       7B      12B  N/A       N    N      idle in trans
    UPDATE pgbench_accounts SET abalance = abalance + 141 WHERE aid = 1932841;
    6228   pgbench                   pgbench         postgres            local    0.2  1.0       0B    1.08M  0.000413  N    Y             active
    \_ UPDATE pgbench_accounts SET abalance = abalance + 3062 WHERE aid = 7289374;
    1234   business               accounting              bob            local    2.4  1.0    9.42M    1.21K  20:34.00  Y    N             active
    SELECT product_id, p.name FROM products p LEFT JOIN sales s USING (product_id)
    WHERE s.date > CURRENT_DATE - INTERVAL '4 weeks' GROUP BY product_id, p.name,
    p.price, p.cost HAVING sum(p.price * s.units) > 5000;

    >>> oneflag = Flag.DATABASE
    >>> processes_rows(term, processes, is_local=True, flag=oneflag,
    ...                query_mode=QueryMode.activities,
    ...                verbose_mode=QueryDisplayMode.truncate)
    6239   pgbench               idle in trans   UPDATE pgbench_accounts SET abalanc
    6228   pgbench                      active   \_ UPDATE pgbench_accounts SET abal
    1234   business                     active   SELECT product_id, p.name FROM prod

    >>> processes_rows(term, processes, is_local=True, flag=oneflag,
    ...                query_mode=QueryMode.activities,
    ...                verbose_mode=QueryDisplayMode.wrap)
    6239   pgbench               idle in trans   UPDATE pgbench_accounts SET
                                                 abalance = abalance + 141 WHERE aid
                                                 = 1932841;
    6228   pgbench                      active   \_ UPDATE pgbench_accounts SET
                                                 abalance = abalance + 3062 WHERE
                                                 aid = 7289374;
    1234   business                     active   SELECT product_id, p.name FROM
                                                 products p LEFT JOIN sales s USING
                                                 (product_id) WHERE s.date >
                                                 CURRENT_DATE - INTERVAL '4 weeks'
                                                 GROUP BY product_id, p.name,
                                                 p.price, p.cost HAVING sum(p.price
                                                 * s.units) > 5000;

    >>> processes = [
    ...     ActivityBW(
    ...         pid="6239",
    ...         appname="pgbench",
    ...         database="pgbench",
    ...         user="postgres",
    ...         mode="ExclusiveLock",
    ...         type="transactionid",
    ...         relation="None",
    ...         duration=666,
    ...         state="active",
    ...         query="END;"
    ...     ),
    ...     ActivityBW(
    ...         pid="6228",
    ...         appname="pgbench",
    ...         database="pgbench",
    ...         user="postgres",
    ...         mode="RowExclusiveLock",
    ...         type="tuple",
    ...         relation="ahah",
    ...         duration=0.000413,
    ...         state="idle in transaction",
    ...         query="UPDATE pgbench_branches SET bbalance = bbalance + 1788 WHERE bid = 68;",
    ...     ),
    ... ]
    >>> processes_rows(term, processes, is_local=True, flag=oneflag,
    ...                query_mode=QueryMode.waiting,
    ...                verbose_mode=QueryDisplayMode.wrap)
    6239   pgbench                      active   END;
    6228   pgbench               idle in trans   UPDATE pgbench_branches SET
                                                 bbalance = bbalance + 1788 WHERE
                                                 bid = 68;
    >>> processes_rows(term, processes, is_local=False, flag=allflags,
    ...                query_mode=QueryMode.blocking)  # doctest: +NORMALIZE_WHITESPACE
    6239   pgbench                   pgbench      None    transactionid    ExclusiveLock  11:06.00             active
    END;
    6228   pgbench                   pgbench      ahah            tuple RowExclusiveLock  0.000413      idle in trans
    UPDATE pgbench_branches SET bbalance = bbalance + 1788 WHERE bid = 68;
    """

    # if color_type == 'default' and self.pid_yank.count(process['pid']) > 0:
    # color_type = 'yellow'

    def color_for(field: str) -> FormattingString:
        return getattr(term, LINE_COLORS[field][color_type])

    def template_for(column_name: str) -> str:
        return getattr(Column, column_name).value.template_h  # type: ignore

    def text_append(value: str) -> None:
        # We also restore 'normal' style so that the next item does not
        # inherit previous one's style.
        text.append(value + term.normal)

    def cell(
        process: Union[Activity, ActivityProcess],
        key: str,
        crop: Optional[int],
        transform: Callable[[Any], str] = str,
        color_key: Optional[str] = None,
    ) -> None:
        column_value = transform(getattr(process, key))[:crop]
        color_key = color_key or key
        text_append(f"{color_for(color_key)}{template_for(key) % column_value}")

    naturalsize = functools.partial(humanize.naturalsize, gnu=True, format="%.2f")

    for process in processes:
        text: List[str] = []
        cell(process, "pid", None)

        if flag & Flag.DATABASE:
            cell(process, "database", 16)
        if flag & Flag.APPNAME:
            cell(process, "appname", 16)
        if query_mode == QueryMode.activities:
            if flag & Flag.USER:
                cell(process, "user", 16)
            if flag & Flag.CLIENT:
                cell(process, "client", 16)
            if flag & Flag.CPU:
                cell(process, "cpu", None)
            if flag & Flag.MEM:
                cell(process, "mem", None, lambda v: str(round(v, 1)))
            if flag & Flag.READ:
                cell(process, "read", None, naturalsize)
            if flag & Flag.WRITE:
                cell(process, "write", None, naturalsize)

        elif query_mode in (QueryMode.waiting, QueryMode.blocking):
            if flag & Flag.RELATION:
                cell(process, "relation", 9)
            if flag & Flag.TYPE:
                cell(process, "type", 16)

            if flag & Flag.MODE:
                assert isinstance(process, ActivityBW)
                if process.mode in (
                    "ExclusiveLock",
                    "RowExclusiveLock",
                    "AccessExclusiveLock",
                ):
                    mode_color = "mode_red"
                else:
                    mode_color = "mode_yellow"
                cell(process, "mode", 16, color_key=mode_color)

        if flag & Flag.TIME:
            ctime, color = format_duration(process.duration)
            text_append(f"{color_for(color)}{template_for('time') % ctime}")

        if query_mode == QueryMode.activities and flag & Flag.WAIT:
            if process.wait:
                text_append(f"{color_for('wait_red')}{template_for('wait') % 'Y'}")
            else:
                text_append(f"{color_for('wait_green')}{template_for('wait') % 'N'}")

        if (
            isinstance(process, ActivityProcess)
            and query_mode == QueryMode.activities
            and flag & Flag.IOWAIT
        ):
            assert process.io_wait in "YN", process.io_wait
            if process.io_wait == "Y":
                text_append(f"{color_for('wait_red')}{template_for('iowait') % 'Y'}")
            else:
                text_append(f"{color_for('wait_green')}{template_for('iowait') % 'N'}")

        state = utils.short_state(process.state)
        if state == "active":
            color_state = "state_green"
        elif state == "idle in trans":
            color_state = "state_yellow"
        elif state == "idle in trans (a)":
            color_state = "state_red"
        else:
            color_state = "state_default"
        text_append(f"{color_for(color_state)}{template_for('state') % state}")

        indent = get_indent(query_mode, flag) + " "
        dif = term.width - len(indent)

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
                    query_lines = [""] + term.wrap(query_r, width=term.width)
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


def screen(
    term: Terminal,
    *,
    host: Host,
    dbinfo: DBInfo,
    tps: int,
    active_connections: int,
    duration_mode: DurationMode,
    refresh_time: float,
    min_duration: float = 0,
    max_iops: int = 0,
    system_info: Optional[SystemInfo] = None,
    querymode: QueryMode,
    flag: Flag,
    sort_key: SortKey,
    activities: Union[Iterable[Activity], Iterable[ActivityProcess]],
    is_local: bool,
    verbose_mode: QueryDisplayMode,
    in_pause: bool,
) -> None:
    """Display the screen."""
    print(term.clear + term.home, end="")
    lines_counter = line_counter(term.height - 1)
    header(
        term,
        host,
        dbinfo,
        tps,
        active_connections,
        duration_mode,
        refresh_time,
        min_duration=min_duration,
        max_iops=max_iops,
        system_info=system_info,
        lines_counter=lines_counter,
    )

    query_mode(term, querymode, in_pause=in_pause, lines_counter=lines_counter)
    columns_header(term, querymode, flag, sort_key, lines_counter=lines_counter)
    processes_rows(
        term,
        activities,
        is_local=is_local,
        flag=flag,
        query_mode=querymode,
        verbose_mode=verbose_mode,
        lines_counter=lines_counter,
    )
