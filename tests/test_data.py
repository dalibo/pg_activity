import pytest
from psycopg2.errors import WrongObjectType

from pgactivity.data import Data
from conftest import PgThreadCoord


@pytest.fixture
def data(postgresql):
    return Data.pg_connect(
        min_duration=0.0,
        host=postgresql.info.host,
        port=postgresql.info.port,
        database=postgresql.info.dbname,
        user=postgresql.info.user,
    )


def test_pg_is_local(postgresql, data):
    assert data.pg_is_local()


def test_pg_is_local_access(postgresql, data):
    assert data.pg_is_local_access()


def test_pg_get_db_info(data):
    dbinfo = data.pg_get_db_info(None)
    assert set(dbinfo) == {
        "timestamp",
        "no_xact",
        "total_size",
        "max_length",
        "tps",
        "size_ev",
    }


def test_activities(postgresql, data):
    with postgresql.cursor() as cur:
        cur.execute("SELECT pg_sleep(1)")
    (running,) = data.pg_get_activities()
    assert "pg_sleep" in running.query
    assert running.state == "idle in transaction"
    if postgresql.server_version >= 100000:
        assert running.wait == "ClientRead"
    else:
        assert running.wait is None
    assert not running.is_parallel_worker


def test_blocking_waiting(postgresql, data):
    tc = PgThreadCoord(postgresql.info.dsn_parameters)
    try:
        with postgresql.cursor() as cur:
            cur.execute("CREATE TABLE t (s text)")
            cur.execute("INSERT INTO t VALUES ('init')")
        postgresql.commit()

        tc.execute_thread("UPDATE t SET s = 'blocking'", idle_in_transaction=True)
        tc.execute_thread("UPDATE t SET s = 'waiting 1'", wait_locked=True)
        tc.execute_thread("UPDATE t SET s = 'waiting 2'", wait_locked=True)

        blocking = data.pg_get_blocking()
        waiting = data.pg_get_waiting()

        assert len(blocking) == 2
        assert len(waiting) == 2
        assert "blocking" in blocking[0].query
        assert "waiting" in waiting[0].query
        assert "waiting" in waiting[1].query
        if postgresql.server_version >= 100000:
            assert blocking[0].wait == "ClientRead"
        assert str(blocking[0].type) == "transactionid"
    finally:
        tc.cleanup()


def test_pg_get_blocking_virtualxid(postgresql, data):
    tc = PgThreadCoord(postgresql.info.dsn_parameters)
    try:
        with postgresql.cursor() as cur:
            cur.execute("CREATE TABLE t(s text)")
            cur.execute("INSERT INTO t VALUES ('init')")
        postgresql.commit()

        tc.execute_thread("UPDATE t SET s = 'blocking'", idle_in_transaction=True)
        tc.execute_thread(
            "CREATE INDEX CONCURRENTLY ON t(s)", autocommit=True, wait_locked=True
        )

        (blocking,) = data.pg_get_blocking()
        (waiting,) = data.pg_get_waiting()

        assert "blocking" in blocking.query
        assert "CREATE INDEX CONCURRENTLY ON t(s)" in waiting.query
        assert str(blocking.type) == "virtualxid"
    finally:
        tc.cleanup()


def test_cancel_backend(postgresql, data):
    with postgresql.cursor() as cur:
        cur.execute("SELECT pg_sleep(1)")
    (running,) = data.pg_get_activities()
    assert data.pg_cancel_backend(running.pid)


def test_terminate_backend(postgresql, data):
    with postgresql.cursor() as cur:
        cur.execute("SELECT pg_sleep(1)")
    (running,) = data.pg_get_activities()
    assert data.pg_terminate_backend(running.pid)
    assert not data.pg_get_activities()


def test_pg_get_active_connections(data, postgresql):
    tc = PgThreadCoord(postgresql.info.dsn_parameters)
    try:
        assert data.pg_get_active_connections() == 1
        tc.execute_thread("select pg_sleep(2)")
        assert data.pg_get_active_connections() == 2
    finally:
        tc.cleanup()


def test_encoding(postgresql, data):
    """Test for issue #149"""
    tc = PgThreadCoord(postgresql.info.dsn_parameters)
    try:
        postgresql.set_session(autocommit=True)
        with postgresql.cursor() as cur:
            # plateform specific locales (,Centos, Ubuntu)
            for encoding in ["fr_FR.latin1", "fr_FR.88591", "fr_FR.8859-1"]:
                try:
                    cur.execute(
                        f"CREATE DATABASE latin1 ENCODING 'latin1' TEMPLATE template0 LC_COLLATE '{encoding}' LC_CTYPE '{encoding}'"
                    )
                except WrongObjectType:
                    continue
                else:
                    break

        tc.execute_thread(
            "CREATE TABLE tbl(s text)", database="latin1", wait_completion=True
        )
        tc.execute_thread(
            "INSERT INTO tbl(s) VALUES ('initilialized éléphant')",
            database="latin1",
            wait_completion=True,
        )
        tc.execute_thread(
            "UPDATE tbl SET s = 'blocking éléphant'",
            database="latin1",
            idle_in_transaction=True,
        )
        tc.execute_thread(
            "UPDATE tbl SET s = 'waiting éléphant'", database="latin1", wait_locked=True
        )

        running = data.pg_get_activities()
        (waiting,) = data.pg_get_waiting()
        (blocking,) = data.pg_get_blocking()

        assert (
            "éléphant" in running[0].query
        )  # could be any éléphant first with threads
        assert "waiting éléphant" in waiting.query
        assert "blocking éléphant" in blocking.query
    finally:
        tc.cleanup()
