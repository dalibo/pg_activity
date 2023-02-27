import os
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    TypeVar,
    Union,
    overload,
)

Row = TypeVar("Row")

try:
    if "_PGACTIVITY_USE_PSYCOPG2" in os.environ:
        raise ImportError("psycopg2 requested from environment")

    import psycopg
    from psycopg import sql as sql
    from psycopg.adapt import Buffer, Loader
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

    class BytesLoader(Loader):
        def load(self, data: Buffer) -> bytes:
            if isinstance(data, memoryview):
                return bytes(data)
            return data

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
        conn.execute(query, args, prepare=True)

    @overload
    def cursor(
        conn: Connection, mkrow: Callable[..., Row], text_as_bytes: bool
    ) -> psycopg.Cursor[Row]:
        ...

    @overload
    def cursor(
        conn: Connection, mkrow: None, text_as_bytes: bool
    ) -> psycopg.Cursor[psycopg.rows.DictRow]:
        ...

    def cursor(
        conn: Connection, mkrow: Optional[Callable[..., Row]], text_as_bytes: bool
    ) -> Union[psycopg.Cursor[psycopg.rows.DictRow], psycopg.Cursor[Row]]:
        if mkrow is not None:
            cur = conn.cursor(row_factory=psycopg.rows.kwargs_row(mkrow))
        else:
            cur = conn.cursor()  # type: ignore[assignment]
        if text_as_bytes:
            cur.adapters.register_loader("text", BytesLoader)
        return cur

    @overload
    def fetchone(
        conn: Connection,
        query: Union[str, sql.Composed],
        args: Union[None, Sequence[Any], Dict[str, Any]] = None,
        *,
        mkrow: Callable[..., Row],
        text_as_bytes: bool = False,
    ) -> Row:
        ...

    @overload
    def fetchone(
        conn: Connection,
        query: Union[str, sql.Composed],
        args: Union[None, Sequence[Any], Dict[str, Any]] = None,
        *,
        text_as_bytes: bool = False,
    ) -> Dict[str, Any]:
        ...

    def fetchone(
        conn: Connection,
        query: Union[str, sql.Composed],
        args: Union[None, Sequence[Any], Dict[str, Any]] = None,
        *,
        mkrow: Optional[Callable[..., Row]] = None,
        text_as_bytes: bool = False,
    ) -> Union[Dict[str, Any], Row]:
        with cursor(conn, mkrow, text_as_bytes) as cur:
            row = cur.execute(query, args, prepare=True).fetchone()
        assert row is not None
        return row

    @overload
    def fetchall(
        conn: Connection,
        query: Union[str, sql.Composed],
        args: Union[None, Sequence[Any], Dict[str, Any]] = None,
        *,
        mkrow: Callable[..., Row],
        text_as_bytes: bool = False,
    ) -> List[Row]:
        ...

    @overload
    def fetchall(
        conn: Connection,
        query: Union[str, sql.Composed],
        args: Union[None, Sequence[Any], Dict[str, Any]] = None,
        *,
        text_as_bytes: bool = False,
    ) -> List[Dict[str, Any]]:
        ...

    def fetchall(
        conn: Connection,
        query: Union[str, sql.Composed],
        args: Union[None, Sequence[Any], Dict[str, Any]] = None,
        *,
        text_as_bytes: bool = False,
        mkrow: Optional[Callable[..., Row]] = None,
    ) -> Union[List[Dict[str, Any]], List[Row]]:
        with cursor(conn, mkrow, text_as_bytes) as cur:
            return cur.execute(query, args, prepare=True).fetchall()

except ImportError:
    import psycopg2
    import psycopg2.extensions
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

    def fetchone(  # type: ignore[no-redef]
        conn: Connection,
        query: Union[str, sql.Composed],
        args: Union[None, Sequence[Any], Dict[str, Any]] = None,
        *,
        mkrow: Optional[Callable[..., Row]] = None,
        text_as_bytes: bool = False,
    ) -> Union[Dict[str, Any], Row]:
        with conn.cursor() as cur:
            if text_as_bytes:
                psycopg2.extensions.register_type(psycopg2.extensions.BYTES, cur)
            cur.execute(query, args)
            row = cur.fetchone()
        assert row is not None
        if mkrow is not None:
            return mkrow(**row)
        return row

    def fetchall(  # type: ignore[no-redef]
        conn: Connection,
        query: Union[str, sql.Composed],
        args: Union[None, Sequence[Any], Dict[str, Any]] = None,
        *,
        mkrow: Optional[Callable[..., Row]] = None,
        text_as_bytes: bool = False,
    ) -> Union[List[Dict[str, Any]], List[Row]]:
        with conn.cursor() as cur:
            if text_as_bytes:
                psycopg2.extensions.register_type(psycopg2.extensions.BYTES, cur)
            cur.execute(query, args)
            rows = cur.fetchall()
        if mkrow is not None:
            return [mkrow(**row) for row in rows]
        return rows


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
