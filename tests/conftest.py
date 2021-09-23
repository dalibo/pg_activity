import asyncio
import pathlib
import threading
from typing import Optional

import psycopg2
import psycopg2.errors
import pytest


@pytest.fixture(scope="session")
def datadir() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "data"


@pytest.fixture
def execute(postgresql):
    """Create a thread and return an execute() function that will run SQL queries in that
    thread.
    """
    cnx = []

    loop = asyncio.new_event_loop()

    def execute(
        query: str,
        commit: bool = False,
        autocommit: bool = False,
        dbname: Optional[str] = None,
    ) -> None:
        def _execute() -> None:
            connection_parms = postgresql.info.dsn_parameters
            if dbname:
                connection_parms["dbname"] = dbname
            conn = psycopg2.connect(**connection_parms)
            conn.autocommit = autocommit
            cnx.append(conn)
            with conn.cursor() as c:
                try:
                    c.execute(query)
                except (
                    psycopg2.errors.AdminShutdown,
                    psycopg2.errors.QueryCanceledError,
                ):
                    return
                if not autocommit and commit:
                    conn.commit()

        loop.call_soon_threadsafe(_execute)

    def run_loop() -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()

    yield execute

    for conn in cnx:
        loop.call_soon_threadsafe(conn.close)
    loop.call_soon_threadsafe(loop.stop)

    thread.join(timeout=2)
