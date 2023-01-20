import os
from typing import Any, Dict, List, Sequence, Union

try:
    if "_PGACTIVITY_USE_PSYCOPG2" in os.environ:
        raise ImportError("psycopg2 requested from environment")

    import psycopg
    from psycopg import sql as sql
    from psycopg.rows import dict_row
    from psycopg.errors import (
        FeatureNotSupported as FeatureNotSupported,
        InterfaceError as InterfaceError,
        InvalidPassword as InvalidPassword,
        InsufficientPrivilege as InsufficientPrivilege,
        OperationalError as OperationalError,
        ProgrammingError as ProgrammingError,
        QueryCanceled as QueryCanceled,
    )

    __version__ = psycopg.__version__

    Connection = psycopg.Connection[Dict[str, Any]]

    def connect(*args: Any, **kwargs: Any) -> Connection:
        return psycopg.connect(*args, autocommit=True, row_factory=dict_row, **kwargs)

    def server_version(conn: Connection) -> int:
        return conn.info.server_version

    def connection_parameters(conn: Connection) -> Dict[str, Any]:
        return conn.info.get_parameters()

    def execute(
        conn: Connection,
        query: Union[str, sql.Composed],
        args: Union[None, Sequence[Any], Dict[str, Any]] = None,
    ) -> None:
        conn.execute(query, args)

    def fetchone(
        conn: Connection,
        query: Union[str, sql.Composed],
        args: Union[None, Sequence[Any], Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        row = conn.execute(query, args).fetchone()
        assert row is not None
        return row

    def fetchall(
        conn: Connection,
        query: Union[str, sql.Composed],
        args: Union[None, Sequence[Any], Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return conn.execute(query, args).fetchall()

except ImportError:
    import psycopg2
    from psycopg2.extras import DictCursor
    from psycopg2 import sql as sql  # type: ignore[no-redef]
    from psycopg2.errors import (  # type: ignore[no-redef]
        FeatureNotSupported as FeatureNotSupported,
        InterfaceError as InterfaceError,
        InvalidPassword as InvalidPassword,
        InsufficientPrivilege as InsufficientPrivilege,
        OperationalError as OperationalError,
        ProgrammingError as ProgrammingError,
        QueryCanceled as QueryCanceled,
    )

    from psycopg2.extensions import connection as Connection  # type: ignore[no-redef]

    __version__ = psycopg2.__version__

    def connect(*args: Any, **kwargs: Any) -> Connection:
        try:
            kwargs.setdefault("database", kwargs.pop("dbname"))
        except KeyError:
            pass
        conn = psycopg2.connect(*args, cursor_factory=DictCursor, **kwargs)
        conn.autocommit = True
        return conn  # type: ignore[no-any-return]

    def server_version(conn: Connection) -> int:
        return conn.server_version  # type: ignore[attr-defined, no-any-return]

    def connection_parameters(conn: Connection) -> Dict[str, Any]:
        return conn.info.dsn_parameters  # type: ignore[attr-defined, no-any-return]

    def execute(
        conn: Connection,
        query: Union[str, sql.Composed],
        args: Union[None, Sequence[Any], Dict[str, Any]] = None,
    ) -> None:
        with conn.cursor() as cur:
            cur.execute(query, args)

    def fetchone(
        conn: Connection,
        query: Union[str, sql.Composed],
        args: Union[None, Sequence[Any], Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with conn.cursor() as cur:
            cur.execute(query, args)
            row = cur.fetchone()
        assert row is not None
        return row

    def fetchall(
        conn: Connection,
        query: Union[str, sql.Composed],
        args: Union[None, Sequence[Any], Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(query, args)
            return cur.fetchall()


__all__ = [
    "__version__",
    "Connection",
    "FeatureNotSupported",
    "InterfaceError",
    "InvalidPassword",
    "InsufficientPrivilege",
    "OperationalError",
    "ProgrammingError",
    "QueryCanceled",
    "connect",
    "connection_parameters",
    "execute",
    "fetchall",
    "fetchone",
    "server_version",
    "sql",
]
