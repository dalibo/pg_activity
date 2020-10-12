import getpass
import optparse
import re
import sys
from datetime import datetime
from functools import wraps
from typing import Any, Callable, IO, Iterable, List, Mapping, Optional, TypeVar, Union

import psycopg2
from psycopg2 import errorcodes


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


def csv_write(fobj: IO[str], procs: Iterable[Mapping[str, Any]]) -> None:
    """Store process list into CSV file.

    >>> processes = [
    ...     {'pid': 25199, 'appname': '', 'database': 'pgbench', 'user': None,
    ...      'client': 'local', 'cpu': 0.0, 'mem': 0.6504979545924837,
    ...      'read': 0.0, 'write': 0.0, 'state': 'active',
    ...      'query': 'autovacuum: VACUUM ANALYZE public.pgbench_tellers',
    ...      'duration': 0.348789, 'wait': False,
    ...      'io_wait': 'N', 'is_parallel_worker': False},
    ...     {'pid': 25068, 'appname': 'pgbench', 'database': 'pgbench', 'user':
    ...      'postgres', 'client': 'local', 'cpu': 0.0, 'mem': 2.4694780629380646,
    ...      'read': 278536.76590087387, 'write': 835610.2977026217,
    ...      'state': 'idle in transaction',
    ...      'query': 'INSERT INTO pgbench_history (tid, bid, aid, delta, mtime) VALUES (625, 87, 4368910, -341, CURRENT_TIMESTAMP);',
    ...      'duration': 0.000105, 'wait': False, 'io_wait': 'N',
    ...      'is_parallel_worker': False},
    ...     {'pid': 25379, 'appname': 'pgbench', 'database': 'pgbench',
    ...      'user': 'postgres', 'client': 'local', 'state': 'active',
    ...      'query': 'UPDATE pgbench_branches SET bbalance = bbalance + -49 WHERE bid = 73;',
    ...      'duration': 0, 'wait': False},
    ...     {'pid': 25392, 'appname': 'pgbench', 'database': 'pgbench',
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
    "...-...-...T...Z";"25199";"pgbench";"";"None";"local";"0.0";"0.6504979545924837";"0.0";"0.0";"0.348789";"False";"N";"active";"autovacuum: VACUUM ANALYZE public.pgbench_tellers"
    "...-...-...T...Z";"25068";"pgbench";"pgbench";"postgres";"local";"0.0";"2.4694780629380646";"278536.76590087387";"835610.2977026217";"0.000105";"False";"N";"idle in transaction";"INSERT INTO pgbench_history (tid, bid, aid, delta, mtime) VALUES (625, 87, 4368910, -341, CURRENT_TIMESTAMP);"
    "...-...-...T...Z";"25379";"pgbench";"pgbench";"postgres";"local";"N/A";"N/A";"N/A";"N/A";"0";"False";"N/A";"active";"UPDATE pgbench_branches SET bbalance = bbalance + -49 WHERE bid = 73;"
    "...-...-...T...Z";"25392";"pgbench";"pgbench";"postgres";"local";"N/A";"N/A";"N/A";"N/A";"0";"False";"N/A";"active";"BEGIN;"
    """

    def clean_str_csv(s: str) -> str:
        return clean_str(s).replace('"', '\\"')

    if fobj.tell() == 0:
        # First line then write CSV header
        fobj.write(
            "datetimeutc;pid;database;appname;user;client;cpu;"
            "memory;read;write;duration;wait;io_wait;state;"
            "query\n"
        )

    for p in procs:
        dt = datetime.utcnow().strftime("%Y-%m-%dT%H:%m:%SZ")
        pid = p.get("pid", "N/A")
        database = p.get("database", "N/A")
        appname = p.get("appname", "N/A")
        user = p.get("user", "N/A")
        client = p.get("client", "N/A")
        cpu = p.get("cpu", "N/A")
        mem = p.get("mem", "N/A")
        read = p.get("read", "N/A")
        write = p.get("write", "N/A")
        duration = p.get("duration", "N/A")
        wait = p.get("wait", "N/A")
        io_wait = p.get("io_wait", "N/A")
        state = p.get("state", "N/A")
        query = clean_str_csv(p.get("query", "N/A"))
        fobj.write(
            f'"{dt}";"{pid}";"{database}";"{appname}";"{user}";"{client}";"{cpu}";"{mem}";'
            f'"{read}";"{write}";"{duration}";"{wait}";"{io_wait}";"{state}";"{query}"\n'
        )


R = TypeVar("R")


def return_as(
    c: Callable[..., R]
) -> Callable[[Callable[..., Any]], Callable[..., List[R]]]:
    """Decorator casting the result of wrapped function with 'c'. The 'result'
    should be a list.

    >>> from typing import Any, Dict, List

    >>> def to_lowercase(**kwargs: Any) -> Dict[str, Any]:
    ...     return {k.lower():v  for k, v in kwargs.items()}
    >>> to_lowercase(A=1, b=2)
    {'a': 1, 'b': 2}

    >>> @return_as(to_lowercase)
    ... def query() -> List[Dict[str, int]]:
    ...     return [{'A': 1}, {'b': 2}]

    >>> query()
    [{'a': 1}, {'b': 2}]
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., List[R]]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Union[List[R], R]:
            result = func(*args, **kwargs)
            assert isinstance(result, list), f"{func} must return a list value"
            return [c(**item) for item in result]

        return wrapper

    return decorator


def pg_connect(
    data: Any,
    options: optparse.Values,
    password: Optional[str] = None,
    service: Optional[str] = None,
    exit_on_failed: bool = True,
) -> Optional[str]:
    """Try to connect to postgres using 'data' instance, return the password
    to be used in case of reconnection.
    """
    for nb_try in range(2):
        try:
            data.pg_connect(
                host=options.host,
                port=options.port,
                user=options.username,
                password=password,
                database=options.dbname,
                rds_mode=options.rds,
                service=service,
            )
        except psycopg2.OperationalError as err:
            errmsg = str(err).strip()
            if nb_try < 1 and (
                err.pgcode == errorcodes.INVALID_PASSWORD
                or errmsg.startswith("FATAL:  password authentication failed for user")
                or errmsg == "fe_sendauth: no password supplied"
            ):
                password = getpass.getpass()
            elif exit_on_failed:
                msg = str(err).replace("FATAL:", "")
                sys.exit("pg_activity: FATAL: %s" % clean_str(msg))
            else:
                raise Exception("Could not connect to PostgreSQL")
        else:
            break
    return password
