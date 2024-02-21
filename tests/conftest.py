from __future__ import annotations

import logging
import pathlib
import threading
from typing import Any

import psycopg
import psycopg.errors
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from pgactivity import pg

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


def pytest_report_header(config: Any) -> list[str]:
    return [f"psycopg: {pg.__version__}"]


@pytest.fixture(scope="session")
def datadir() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "data"


@pytest.fixture
def database_factory(postgresql):
    dbnames = set()

    def createdb(dbname: str, encoding: str, locale: str | None = None) -> None:
        with psycopg.connect(postgresql.info.dsn, autocommit=True) as conn:
            qs = sql.SQL(
                "CREATE DATABASE {dbname} ENCODING {encoding} TEMPLATE template0"
            ).format(dbname=sql.Identifier(dbname), encoding=sql.Identifier(encoding))
            if locale:
                qs = sql.SQL(" ").join(
                    [
                        qs,
                        sql.SQL("LOCALE {locale}").format(
                            locale=sql.Identifier(locale)
                        ),
                    ]
                )
            conn.execute(qs)
        dbnames.add(dbname)

    yield createdb

    with psycopg.connect(postgresql.info.dsn, autocommit=True) as conn:
        for dbname in dbnames:
            conn.execute(
                sql.SQL("DROP DATABASE IF EXISTS {dbname} WITH (FORCE)").format(
                    dbname=sql.Identifier(dbname)
                )
            )


@pytest.fixture
def execute(postgresql):
    """Create a thread and return an execute() function that will run SQL queries in that
    thread.
    """
    threads_and_cnx = []

    def execute(
        query: str,
        commit: bool = False,
        autocommit: bool = False,
        dbname: str | None = None,
    ) -> None:
        dsn, kwargs = postgresql.info.dsn, {}
        if dbname:
            kwargs["dbname"] = dbname
        conn = psycopg.connect(make_conninfo(dsn, **kwargs))
        conn.autocommit = autocommit

        def _execute() -> None:
            LOGGER.info(
                "running query %s (commit=%s, autocommit=%s) using connection <%s>",
                query,
                commit,
                autocommit,
                id(conn),
            )
            with conn.cursor() as c:
                try:
                    c.execute(query)
                except (
                    psycopg.errors.AdminShutdown,
                    psycopg.errors.QueryCanceled,
                ):
                    return
                if not autocommit and commit:
                    conn.commit()
            LOGGER.info("query %s finished", query)

        thread = threading.Thread(target=_execute, daemon=True)
        thread.start()
        threads_and_cnx.append((thread, conn))

    yield execute

    for thread, conn in threads_and_cnx:
        thread.join(timeout=2)
        LOGGER.info("closing connection <%s>", id(conn))
        conn.close()
