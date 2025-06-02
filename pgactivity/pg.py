from __future__ import annotations

import logging
import os
from collections.abc import Callable, Sequence
from typing import Any, TypeVar, overload

Row = TypeVar("Row")

try:
    if "_PGACTIVITY_USE_PSYCOPG2" in os.environ:
        raise ImportError("psycopg2 requested from environment")

    import psycopg
    from psycopg import sql as sql
    from psycopg._encodings import pg2pyenc
    from psycopg.adapt import Buffer, Loader
    from psycopg.conninfo import conninfo_to_dict, make_conninfo
    from psycopg.errors import FeatureNotSupported as FeatureNotSupported
    from psycopg.errors import InsufficientPrivilege as InsufficientPrivilege
    from psycopg.errors import InterfaceError as InterfaceError
    from psycopg.errors import InvalidPassword as InvalidPassword
    from psycopg.errors import NotSupportedError
    from psycopg.errors import OperationalError as OperationalError
    from psycopg.errors import ProgrammingError as ProgrammingError
    from psycopg.errors import QueryCanceled as QueryCanceled
    from psycopg.rows import dict_row

    __version__ = psycopg.__version__

    Connection = psycopg.Connection[dict[str, Any]]

    class BytesLoader(Loader):
        def load(self, data: Buffer) -> bytes | bytearray:
            if isinstance(data, memoryview):
                return bytes(data)
            return data

    class AutoTextLoader(Loader):
        def load(self, data: Buffer) -> str:
            if not isinstance(data, bytes):
                data = bytes(data)
            return data.decode(errors="replace")

    def connect(dsn: str = "", **kwargs: Any) -> Connection:
        if "PGCLIENTENCODING" not in os.environ:
            # Set client_encoding to 'auto', if not set by the user.
            # This is (more or less) what's done by psql.
            conninfo = conninfo_to_dict(dsn)
            conninfo.setdefault("client_encoding", "auto")
            dsn = make_conninfo("", **conninfo)
        conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row, **kwargs)
        if conn.info.encoding == "ascii":
            # If client encoding is still 'ascii', fall back to a loader with a replace
            # policy.
            logging.getLogger("pgactivity").warning(
                "client encoding is 'ascii', using a fallback loader for character types"
            )
            conn.adapters.register_loader("text", AutoTextLoader)
            conn.adapters.register_loader("varchar", AutoTextLoader)
            conn.adapters.register_loader('"char"', AutoTextLoader)
        return conn

    def server_version(conn: Connection) -> int:
        return conn.info.server_version

    def connection_parameters(conn: Connection) -> dict[str, Any]:
        return conn.info.get_parameters()

    def execute(
        conn: Connection,
        query: str | sql.Composed,
        args: None | Sequence[Any] | dict[str, Any] = None,
    ) -> None:
        conn.execute(query, args, prepare=True)

    @overload
    def cursor(
        conn: Connection, mkrow: Callable[..., Row], text_as_bytes: bool
    ) -> psycopg.Cursor[Row]: ...

    @overload
    def cursor(
        conn: Connection, mkrow: None, text_as_bytes: bool
    ) -> psycopg.Cursor[psycopg.rows.DictRow]: ...

    def cursor(
        conn: Connection, mkrow: Callable[..., Row] | None, text_as_bytes: bool
    ) -> psycopg.Cursor[psycopg.rows.DictRow] | psycopg.Cursor[Row]:
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
        query: str | sql.Composed,
        args: None | Sequence[Any] | dict[str, Any] = None,
        *,
        mkrow: Callable[..., Row],
        text_as_bytes: bool = False,
    ) -> Row: ...

    @overload
    def fetchone(
        conn: Connection,
        query: str | sql.Composed,
        args: None | Sequence[Any] | dict[str, Any] = None,
        *,
        text_as_bytes: bool = False,
    ) -> dict[str, Any]: ...

    def fetchone(
        conn: Connection,
        query: str | sql.Composed,
        args: None | Sequence[Any] | dict[str, Any] = None,
        *,
        mkrow: Callable[..., Row] | None = None,
        text_as_bytes: bool = False,
    ) -> dict[str, Any] | Row:
        with cursor(conn, mkrow, text_as_bytes) as cur:
            row = cur.execute(query, args, prepare=True).fetchone()
        assert row is not None
        return row

    @overload
    def fetchall(
        conn: Connection,
        query: str | sql.Composed,
        args: None | Sequence[Any] | dict[str, Any] = None,
        *,
        mkrow: Callable[..., Row],
        text_as_bytes: bool = False,
    ) -> list[Row]: ...

    @overload
    def fetchall(
        conn: Connection,
        query: str | sql.Composed,
        args: None | Sequence[Any] | dict[str, Any] = None,
        *,
        text_as_bytes: bool = False,
    ) -> list[dict[str, Any]]: ...

    def fetchall(
        conn: Connection,
        query: str | sql.Composed,
        args: None | Sequence[Any] | dict[str, Any] = None,
        *,
        text_as_bytes: bool = False,
        mkrow: Callable[..., Row] | None = None,
    ) -> list[dict[str, Any]] | list[Row]:
        with cursor(conn, mkrow, text_as_bytes) as cur:
            return cur.execute(query, args, prepare=True).fetchall()

    def decode(value: bytes, pgenc: bytes, *, errors: str) -> str:
        """Decode 'value' with PostgreSQL encoding 'pgenc' converted to Python encoding
        name if available.
        """
        try:
            pyenc = pg2pyenc(pgenc)
        except NotSupportedError:
            pyenc = "utf-8"
        return value.decode(pyenc, errors=errors)

    def needs_password(exc: OperationalError) -> bool:
        assert exc.pgconn is not None
        return exc.pgconn.needs_password

except ImportError:
    import codecs

    import psycopg2
    import psycopg2.extensions
    from psycopg2 import sql as sql  # type: ignore[no-redef]

    # isort: off
    from psycopg2.errors import FeatureNotSupported as FeatureNotSupported  # type: ignore[assignment]
    from psycopg2.errors import InsufficientPrivilege as InsufficientPrivilege  # type: ignore[assignment]
    from psycopg2.errors import InterfaceError as InterfaceError  # type: ignore[assignment]
    from psycopg2.errors import InvalidPassword as InvalidPassword  # type: ignore[assignment]
    from psycopg2.errors import OperationalError as OperationalError  # type: ignore[assignment]
    from psycopg2.errors import ProgrammingError as ProgrammingError  # type: ignore[assignment]
    from psycopg2.errors import QueryCanceled as QueryCanceled  # type: ignore[assignment]

    # isort: on
    from psycopg2.extensions import connection as Connection  # type: ignore[assignment]
    from psycopg2.extras import DictCursor

    __version__ = psycopg2.__version__  # type: ignore[attr-defined]

    def connect(dsn: str = "", **kwargs: Any) -> Connection:
        try:
            kwargs.setdefault("database", kwargs.pop("dbname"))
        except KeyError:
            pass
        conn = psycopg2.connect(dsn, cursor_factory=DictCursor, **kwargs)
        conn.autocommit = True
        return conn  # type: ignore[no-any-return]

    def server_version(conn: Connection) -> int:
        return conn.server_version  # type: ignore[attr-defined, no-any-return]

    def connection_parameters(conn: Connection) -> dict[str, Any]:
        return conn.info.dsn_parameters  # type: ignore[attr-defined, no-any-return]

    def execute(
        conn: Connection,
        query: str | sql.Composed,
        args: None | Sequence[Any] | dict[str, Any] = None,
    ) -> None:
        with conn.cursor() as cur:
            cur.execute(query, args)

    def fetchone(  # type: ignore[no-redef]
        conn: Connection,
        query: str | sql.Composed,
        args: None | Sequence[Any] | dict[str, Any] = None,
        *,
        mkrow: Callable[..., Row] | None = None,
        text_as_bytes: bool = False,
    ) -> dict[str, Any] | Row:
        with conn.cursor() as cur:
            if text_as_bytes:
                psycopg2.extensions.register_type(psycopg2.extensions.BYTES, cur)  # type: ignore[arg-type]
            cur.execute(query, args)
            row = cur.fetchone()
        assert row is not None
        if mkrow is not None:
            return mkrow(**row)
        return row

    def fetchall(  # type: ignore[no-redef]
        conn: Connection,
        query: str | sql.Composed,
        args: None | Sequence[Any] | dict[str, Any] = None,
        *,
        mkrow: Callable[..., Row] | None = None,
        text_as_bytes: bool = False,
    ) -> list[dict[str, Any]] | list[Row]:
        with conn.cursor() as cur:
            if text_as_bytes:
                psycopg2.extensions.register_type(psycopg2.extensions.BYTES, cur)  # type: ignore[arg-type]
            cur.execute(query, args)
            rows = cur.fetchall()
        if mkrow is not None:
            return [mkrow(**row) for row in rows]
        return rows

    def decode(value: bytes, pgenc: bytes, *, errors: str) -> str:
        """Decode 'value' with PostgreSQL encoding 'pgenc' converted to Python encoding
        name if available.
        """
        try:
            pyenc = codecs.lookup(pgenc.decode()).name
        except LookupError:
            pyenc = "utf-8"
        return value.decode(pyenc, errors=errors)

    def needs_password(exc: OperationalError) -> bool:
        if isinstance(exc, InvalidPassword):
            return True
        msg = str(exc)
        return (
            msg.startswith("FATAL:  password authentication failed for user")
            or "fe_sendauth: no password supplied" in msg
        )


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
    "decode",
    "execute",
    "fetchall",
    "fetchone",
    "server_version",
    "sql",
]
