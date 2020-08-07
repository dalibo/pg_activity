import getpass
import optparse
import re
import sys
from functools import wraps
from typing import Any, Callable, List, Optional, TypeVar, Union

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
