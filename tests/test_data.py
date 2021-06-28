import time

import pytest

from pgactivity.data import Data


@pytest.fixture
def data(postgresql):
    return Data.pg_connect(
        1,
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


def test_blocking_waiting(postgresql, data, execute):
    with postgresql.cursor() as cur:
        cur.execute("CREATE TABLE t (s text)")
    postgresql.commit()
    execute("INSERT INTO t VALUES ('init')", commit=True)
    execute("UPDATE t SET s = 'blocking'")
    execute("UPDATE t SET s = 'waiting'", commit=True)
    for _ in range(10):
        time.sleep(0.1)
        try:
            (blocking,) = data.pg_get_blocking()
        except ValueError:
            continue
        break
    else:
        raise AssertionError("timeout")
    (waiting,) = data.pg_get_waiting()
    assert "blocking" in blocking.query
    assert "waiting" in waiting.query
    if postgresql.server_version >= 100000:
        assert blocking.wait == "ClientRead"
    assert str(blocking.type) == "transactionid"


def test_pg_get_blocking_virtualxid(postgresql, data, execute):
    with postgresql.cursor() as cur:
        cur.execute("CREATE TABLE t(s text)")
    postgresql.commit()
    execute("INSERT INTO t VALUES ('init')", commit=True)
    execute("UPDATE t SET s = 'blocking'")
    execute("CREATE INDEX CONCURRENTLY ON t(s)", autocommit=True)
    for _ in range(10):
        time.sleep(0.1)
        try:
            (blocking,) = data.pg_get_blocking()
        except ValueError:
            continue
        break
    else:
        raise AssertionError("timeout")
    (waiting,) = data.pg_get_waiting()
    assert "blocking" in blocking.query
    assert "CREATE INDEX CONCURRENTLY ON t(s)" in waiting.query
    assert str(blocking.type) == "virtualxid"


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


def test_pg_get_active_connections(data, execute):
    assert data.pg_get_active_connections() == 1
    execute("select pg_sleep(1)")
    time.sleep(1)
    assert data.pg_get_active_connections() == 2
