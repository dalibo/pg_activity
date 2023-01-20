from typing import Any, Dict, List, Sequence, Union

import psycopg2
from psycopg2.extras import DictCursor
from psycopg2 import sql as sql
from psycopg2.errors import (
    FeatureNotSupported as FeatureNotSupported,
    InterfaceError as InterfaceError,
    InvalidPassword as InvalidPassword,
    InsufficientPrivilege as InsufficientPrivilege,
    OperationalError as OperationalError,
    ProgrammingError as ProgrammingError,
    QueryCanceled as QueryCanceled,
)

from psycopg2.extensions import connection as Connection


def connect(*args: Any, **kwargs: Any) -> Connection:
    return psycopg2.connect(*args, cursor_factory=DictCursor, **kwargs)


def execute(
    conn: Connection,
    query: str,
    args: Union[None, Sequence[Any], Dict[str, Any]] = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(query, args)


def fetchone(
    conn: Connection,
    query: str,
    args: Union[None, Sequence[Any], Dict[str, Any]] = None,
) -> Dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(query, args)
        row = cur.fetchone()
    assert row is not None
    return row  # type: ignore[no-any-return]


def fetchall(
    conn: Connection,
    query: str,
    args: Union[None, Sequence[Any], Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(query, args)
        return cur.fetchall()  # type: ignore[no-any-return]


__all__ = [
    "Connection",
    "FeatureNotSupported",
    "InterfaceError",
    "InvalidPassword",
    "InsufficientPrivilege",
    "OperationalError",
    "ProgrammingError",
    "QueryCanceled",
    "connect",
    "execute",
    "fetchall",
    "fetchone",
    "sql",
]
