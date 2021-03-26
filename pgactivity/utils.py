import functools
import re
from datetime import datetime, timedelta
from typing import Any, IO, Iterable, List, Mapping, Optional, Tuple

import attr
import humanize


naturalsize = functools.partial(humanize.naturalsize, gnu=True, format="%.2f")


@attr.s(auto_attribs=True, frozen=True, slots=True)
class MessagePile:
    """A pile of message.

    >>> p = MessagePile(2)
    >>> p.send("hello")
    >>> p.get()
    'hello'
    >>> p.send("world")
    >>> p.get()
    'world'
    >>> p.get()
    'world'
    >>> p.get()
    """

    n: int
    messages: List[str] = attr.ib(default=attr.Factory(list), init=False)

    def send(self, message: str) -> None:
        self.messages[:] = [message] * self.n

    def get(self) -> Optional[str]:
        if self.messages:
            return self.messages.pop()
        return None


def yn(value: bool) -> str:
    """Return 'Y' or 'N' for a boolean value.

    >>> yn(True)
    'Y'
    >>> yn(False)
    'N'
    """
    return "Y" if value else "N"


def clean_str(string: str) -> str:
    r"""
    Strip and replace some special characters.

    >>> clean_str("\n")
    ''
    >>> clean_str("\n a a  b   b    c \n\t\n c\v\n")
    'a a b b c c'
    """
    msg = str(string)
    msg = msg.replace("\n", " ")
    msg = re.sub(r"\s+", r" ", msg)
    msg = re.sub(r"^\s", r"", msg)
    msg = re.sub(r"\s$", r"", msg)
    return msg


def ellipsis(v: str, width: int) -> str:
    """Shorten a string to specified width with '...' in the middle.

    >>> ellipsis("loooooooooog", 7)
    'lo...og'
    >>> ellipsis("loooooooooog", 6)
    'lo...g'
    >>> ellipsis("short", 10)
    'short'
    """
    lv = len(v)
    if lv <= width:
        return v
    assert width >= 5
    wl = (width - 3) // 2
    return v[: wl + 1] + "..." + v[-wl:]


def get_duration(duration: Optional[float]) -> float:
    """Return 0 if the given duration is negative else, return the duration.

    >>> get_duration(None)
    0
    >>> get_duration(-10)
    0
    >>> get_duration(12)
    12.0
    """
    if duration is None or float(duration) < 0:
        return 0
    return float(duration)


@functools.lru_cache(maxsize=2)
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


def short_state(state: str) -> str:
    """Return a short version of query state.

    >>> short_state("active")
    'active'
    >>> short_state("idle in transaction")
    'idle in trans'
    >>> short_state("idle in transaction (aborted)")
    'idle in trans (a)'
    """
    return {
        "idle in transaction": "idle in trans",
        "idle in transaction (aborted)": "idle in trans (a)",
    }.get(state, state)


def csv_write(
    fobj: IO[str],
    procs: Iterable[Mapping[str, Any]],
    *,
    delimiter: str = ";",
) -> None:
    """Store process list into CSV file.

    >>> processes = [
    ...     {'pid': 25199, 'application_name': '', 'database': 'pgbench', 'user': None,
    ...      'client': 'local', 'cpu': 0.0, 'mem': 0.6504979545924837,
    ...      'read': 0.0, 'write': 0.0, 'state': 'active',
    ...      'query': 'autovacuum: VACUUM ANALYZE public.pgbench_tellers',
    ...      'duration': 0.348789, 'wait': False,
    ...      'io_wait': False, 'is_parallel_worker': False},
    ...     {'pid': 25068, 'application_name': 'pgbench', 'database': None,
    ...      'user': 'postgres', 'client': 'local', 'cpu': 0.0, 'mem': 2.4694780629380646,
    ...      'read': 278536.76590087387, 'write': 835610.2977026217,
    ...      'state': 'idle in transaction',
    ...      'query': 'INSERT INTO pgbench_history (tid, bid, aid, delta, mtime) VALUES (625, 87, 4368910, -341, CURRENT_TIMESTAMP);',
    ...      'duration': 0.000105, 'wait': False, 'io_wait': False,
    ...      'is_parallel_worker': False},
    ...     {'pid': 25379, 'application_name': 'pgbench', 'database': 'pgbench',
    ...      'user': 'postgres', 'client': 'local', 'state': 'active',
    ...      'query': 'UPDATE pgbench_branches SET bbalance = bbalance + -49 WHERE bid = 73;',
    ...      'duration': 0, 'wait': False},
    ...     {'pid': 25392, 'application_name': 'pgbench', 'database': 'pgbench',
    ...      'user': 'postgres', 'client': 'local', 'state': 'active',
    ...      'query': 'BEGIN;', 'duration': 0, 'wait': False}
    ... ]
    >>> import tempfile
    >>> with tempfile.NamedTemporaryFile(mode='w+') as f:
    ...     csv_write(f, processes[:2])
    ...     csv_write(f, processes[2:])
    ...     _ = f.seek(0)
    ...     content = f.read()
    >>> print(content, end="")  # doctest: +ELLIPSIS
    datetimeutc;pid;database;appname;user;client;cpu;memory;read;write;duration;wait;io_wait;state;query
    "...-...-...T...Z";"25199";"pgbench";"";"None";"local";"0.0";"0.6504979545924837";"0.0";"0.0";"0.348789";"N";"N";"active";"autovacuum: VACUUM ANALYZE public.pgbench_tellers"
    "...-...-...T...Z";"25068";"";"pgbench";"postgres";"local";"0.0";"2.4694780629380646";"278536.76590087387";"835610.2977026217";"0.000105";"N";"N";"idle in transaction";"INSERT INTO pgbench_history (tid, bid, aid, delta, mtime) VALUES (625, 87, 4368910, -341, CURRENT_TIMESTAMP);"
    "...-...-...T...Z";"25379";"pgbench";"pgbench";"postgres";"local";"N/A";"N/A";"N/A";"N/A";"0";"N";"N/A";"active";"UPDATE pgbench_branches SET bbalance = bbalance + -49 WHERE bid = 73;"
    "...-...-...T...Z";"25392";"pgbench";"pgbench";"postgres";"local";"N/A";"N/A";"N/A";"N/A";"0";"N";"N/A";"active";"BEGIN;"
    """

    def clean_str_csv(s: str) -> str:
        return clean_str(s).replace('"', '\\"')

    if fobj.tell() == 0:
        # First line then write CSV header
        fobj.write(
            delimiter.join(
                [
                    "datetimeutc",
                    "pid",
                    "database",
                    "appname",
                    "user",
                    "client",
                    "cpu",
                    "memory",
                    "read",
                    "write",
                    "duration",
                    "wait",
                    "io_wait",
                    "state",
                    "query",
                ]
            )
            + "\n"
        )

    def yn_na(value: Optional[bool]) -> str:
        if value is None:
            return "N/A"
        return yn(value)

    for p in procs:
        dt = datetime.utcnow().strftime("%Y-%m-%dT%H:%m:%SZ")
        pid = p.get("pid", "N/A")
        database = p.get("database", "N/A") or ""
        appname = p.get("application_name", "N/A")
        user = p.get("user", "N/A")
        client = p.get("client", "N/A")
        cpu = p.get("cpu", "N/A")
        mem = p.get("mem", "N/A")
        read = p.get("read", "N/A")
        write = p.get("write", "N/A")
        duration = p.get("duration", "N/A")
        wait = yn_na(p.get("wait"))
        io_wait = yn_na(p.get("io_wait"))
        state = p.get("state", "N/A")
        query = clean_str_csv(p.get("query", "N/A"))
        fobj.write(
            delimiter.join(
                [
                    f'"{dt}"',
                    f'"{pid}"',
                    f'"{database}"',
                    f'"{appname}"',
                    f'"{user}"',
                    f'"{client}"',
                    f'"{cpu}"',
                    f'"{mem}"',
                    f'"{read}"',
                    f'"{write}"',
                    f'"{duration}"',
                    f'"{wait}"',
                    f'"{io_wait}"',
                    f'"{state}"',
                    f'"{query}"',
                ]
            )
            + "\n"
        )
