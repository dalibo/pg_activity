from __future__ import annotations

import time

import attr
import psycopg
import pytest
from psycopg.errors import WrongObjectType

from pgactivity import types
from pgactivity.data import Data


def retry(fct, msg: str, timeout: int = 2):
    count = int(timeout / 0.1)
    for _ in range(count):
        time.sleep(0.1)
        value = fct()
        if value:
            return value
    pytest.fail(msg)


@pytest.fixture
def data(postgresql):
    obj = Data.pg_connect(
        host=postgresql.info.host,
        port=postgresql.info.port,
        database=postgresql.info.dbname,
        user=postgresql.info.user,
    )
    yield obj
    obj.pg_conn.close()


def test_pg_is_local(postgresql, data):
    assert data.pg_is_local()


def test_pg_is_local_access(postgresql, data):
    assert data.pg_is_local_access()


def test_pg_get_server_information(data):
    data.pg_get_server_information(None)


def test_activities(postgresql, data):
    postgresql.execute("SELECT pg_sleep(1)")
    (running,) = data.pg_get_activities()
    assert "pg_sleep" in running.query
    assert running.state == "idle in transaction"
    if postgresql.info.server_version >= 100000:
        assert running.wait == "ClientRead"
    else:
        assert running.wait is None
    assert not running.is_parallel_worker


def test_blocking_waiting(postgresql, data, execute):
    postgresql.execute("CREATE TABLE t AS (SELECT 'init'::text s)")
    postgresql.commit()
    execute("UPDATE t SET s = 'blocking'")
    execute("UPDATE t SET s = 'waiting 1'", commit=True)
    execute("UPDATE t SET s = 'waiting 2'", commit=True)
    blocking = retry(data.pg_get_blocking, msg="could not fetch blocking queries")
    waiting = data.pg_get_waiting()
    assert len(blocking) == 2
    assert len(waiting) == 2
    assert "blocking" in blocking[0].query
    assert "waiting 1" in waiting[0].query and "waiting 2" in waiting[1].query
    if postgresql.info.server_version >= 100000:
        assert blocking[0].wait == "ClientRead"
        assert blocking[1].wait == "transactionid"
    assert str(blocking[0].type) == "transactionid"
    assert str(blocking[1].type) == "tuple"


def test_pg_get_blocking_virtualxid(postgresql, data, execute):
    postgresql.execute("CREATE TABLE t AS (SELECT 'init'::text s)")
    postgresql.commit()
    execute("UPDATE t SET s = 'blocking'")
    execute("CREATE INDEX CONCURRENTLY ON t(s)", autocommit=True)
    (blocking,) = retry(data.pg_get_blocking, msg="could not fetch blocking queries")
    (waiting,) = data.pg_get_waiting()
    assert "blocking" in blocking.query
    assert "CREATE INDEX CONCURRENTLY ON t(s)" in waiting.query
    assert str(blocking.type) == "virtualxid"


def test_cancel_backend(postgresql, data):
    postgresql.execute("SELECT pg_sleep(1)")
    (running,) = data.pg_get_activities()
    assert data.pg_cancel_backend(running.pid)


def test_terminate_backend(postgresql, data):
    postgresql.execute("SELECT pg_sleep(1)")
    (running,) = data.pg_get_activities()
    assert data.pg_terminate_backend(running.pid)
    retry(lambda: not data.pg_get_activities(), msg="some processes are still active")


def test_encoding(postgresql, data, execute):
    """Test for issue #149, #332."""
    conninfo = postgresql.info.dsn
    # plateform specific locales (Centos, Ubuntu)
    encodings = ["fr_FR.latin1", "fr_FR.88591", "fr_FR.8859-1"]
    with psycopg.connect(conninfo, autocommit=True) as conn:
        for encoding in encodings:
            try:
                conn.execute(
                    f"CREATE DATABASE latin1 ENCODING 'latin1' TEMPLATE template0 LC_COLLATE '{encoding}' LC_CTYPE '{encoding}'"
                )
            except WrongObjectType:
                continue
            else:
                break
        else:
            pytest.skip(
                f"could not create a database with encoding amongst {', '.join(encodings)}"
            )

    with psycopg.connect(conninfo, dbname="latin1") as conn:
        conn.execute("CREATE TABLE tbl AS (SELECT 'initilialized éléphant' s)")
        conn.commit()

    execute("UPDATE tbl SET s = 'blocking éléphant'", dbname="latin1")
    execute("UPDATE tbl SET s = 'waiting éléphant'", dbname="latin1", commit=True)
    running = retry(data.pg_get_activities, msg="could not fetch activities")
    assert "blocking éléphant" in running[0].query
    (waiting,) = retry(data.pg_get_waiting, "no waiting process")
    assert waiting.query and "waiting éléphant" in waiting.query
    (blocking,) = data.pg_get_blocking()
    assert blocking.query and "blocking éléphant" in blocking.query


@pytest.mark.parametrize("encoding", ["utf-8", "latin1", "sql_ascii"])
def test_client_encoding(postgresql, encoding: str) -> None:
    data = Data.pg_connect(
        host=postgresql.info.host,
        port=postgresql.info.port,
        database=postgresql.info.dbname,
        user=postgresql.info.user,
        dsn=f"client_encoding={encoding}",
    )
    try:
        assert data.pg_version.startswith(
            f"PostgreSQL {str(postgresql.info.server_version)[:2]}"
        )
    finally:
        data.pg_conn.close()


@pytest.mark.parametrize(
    "pyenc, pgenc, locale",
    [
        ("utf8", "UTF8", None),
        ("ascii", "SQL_ASCII", None),
        ("unknown", "EUC_TW", "zh_TW.euctw"),
    ],
)
def test_postgres_and_python_encoding(
    database_factory, pyenc: str, pgenc: str, locale: str | None, data, postgresql
) -> None:
    dbname = pyenc
    try:
        database_factory(dbname, encoding=pgenc, locale=locale)
    except WrongObjectType:
        pytest.skip(f"could not create a database with encoding '{pgenc}'")
    with psycopg.connect(
        postgresql.info.dsn, dbname=dbname, client_encoding="utf-8"
    ) as conn:
        conn.execute("SELECT 'encoding'")
        (running,) = data.pg_get_activities()
    assert "'encoding'" in running.query
    assert running.encoding == pgenc
    assert running.database == dbname


def test_filters_dbname(data, execute):
    data_filtered = attr.evolve(data, filters=types.Filters(dbname="temp"))
    execute("SELECT pg_sleep(2)", dbname="template1", autocommit=True)
    nbconn = retry(
        data.pg_get_server_information,
        msg="could not get active connections for filtered DBNAME",
    )
    nbconn_filtered = retry(
        data_filtered.pg_get_server_information,
        msg="could not get active connections for filtered DBNAME",
    )
    assert nbconn.active_connections == 2
    assert nbconn_filtered.active_connections == 1
