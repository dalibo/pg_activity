import pathlib
import time
from threading import Thread
from typing import Dict, List, Optional

import psycopg2
import psycopg2.errors
from psycopg2.extensions import (
    TRANSACTION_STATUS_ACTIVE,
    TRANSACTION_STATUS_INTRANS,
    TRANSACTION_STATUS_INERROR,
)
import pytest


@pytest.fixture(scope="session")
def datadir() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "data"


class PgThread(Thread):
    def __init__(
        self: "PgThread",
        connection_string: Dict[str, str],
        query: str,
        idle_in_transaction: bool = False,
        autocommit: bool = False,
    ) -> None:
        """Creates a thread to execute a query

        :param Optional[str] database: the database to connect to if different from the one provided during the creation of the class
        :param str query: query to execute
        :param bool idle_in_transaction: should the transaction remain idle_in_transaction, default False
        :param bool autocommit: should we activate autocommit, default False (usefull for some non transactionnal DDL)
        """
        Thread.__init__(self)
        self.connection_string: Dict[str, str] = connection_string
        self.query: str = query
        self.idle_in_transaction: bool = idle_in_transaction
        self.autocommit: bool = autocommit
        self.conn: Optional[psycopg2.connection] = None

    def run(self: "PgThread") -> None:
        """Execute a query"""
        self.conn = psycopg2.connect(**self.connection_string)
        self.conn.autocommit = self.autocommit
        try:
            with self.conn.cursor() as c:
                c.execute(self.query)
                while self.idle_in_transaction:
                    time.sleep(0.1)
            self.conn.commit()
        except (
            psycopg2.errors.AdminShutdown,
            psycopg2.errors.QueryCanceledError,
        ):
            pass
        self.conn.close()

    def stop_idle_in_transactioning(self: "PgThread") -> None:
        """Remove the idle_in_transaction flag so that we stop waiting"""
        self.idle_in_transaction = False

    def is_idle_in_transaction(self: "PgThread") -> bool:
        """Check if the transaction is ile in transaction

        :rtype: bool
        """
        # This syntaxe is used for mypy otherwise it complains that the value returned could be any
        return (
            True
            if self.conn is not None
            and self.conn.info.transaction_status
            in [TRANSACTION_STATUS_INTRANS, TRANSACTION_STATUS_INERROR]
            else False
        )

    def is_active(self: "PgThread") -> bool:
        """Check if the transaction is active (a command is running)

        :rtype: bool
        :raises Exception: if we are not connected
        """
        # This syntaxe is used for mypy otherwise it complains that the value returned could be any
        return (
            True
            if (
                self.conn is not None
                and self.conn.info.transaction_status == TRANSACTION_STATUS_ACTIVE
            )
            else False
        )

    def is_query_locked(self: "PgThread") -> bool:
        """Check if this session is waiting because of a lock

        :rtype: bool
        :raises Exception: if we are not connected
        """
        if self.conn is not None and not self.conn.closed:
            pid = self.conn.info.backend_pid
            conn = psycopg2.connect(**self.connection_string)
            with conn.cursor() as c:
                # Look for a lock that is not granted for our pid
                c.execute(
                    f"SELECT * FROM pg_locks l WHERE l.pid = {pid} AND NOT l.granted"
                )
                if c.rowcount >= 1:
                    conn.close
                    return True
                else:
                    conn.close
        return False


class PgThreadCoord:
    def __init__(self: "PgThreadCoord", connection_string: Dict[str, str]) -> None:
        """Create a thread coordinator to execute queries on an instance

        :param Dict[str, str] connection_string connection string as presented in psycopg2.connection.info.dsn_parameters
        """
        self.idle_in_transaction_threads: List[PgThread] = []
        self.others_threads: List[PgThread] = []
        self.connection_string: Dict[str, str] = connection_string

    def execute_thread(
        self: "PgThreadCoord",
        query: str,
        database: Optional[str] = None,
        idle_in_transaction: bool = False,
        autocommit: bool = False,
        wait_completion: bool = False,
        wait_locked: bool = False,
    ) -> None:
        """execute a query in a thread

        :param str query: query to execute
        :param Optional[str] database: the database to connect to if different from the one provided during the creation of the class
        :param bool idle_in_transaction: should the transaction remain idle_in_transaction, default False
        :param bool autocommit: should we activate autocommit, default False (usefull for some non transactionnal DDL)
        :param bool wait_completion: wait for the query to finish before continuing the flow of the program
                                     this is usefull quick queries to do the setup of the tests
        :param bool wait_locked: wait for the query to wait for a lock before continuing the flow of the program
                                 this is usefull to check the blocking / waiting queries
        :raises AssertionError: if we wait for more than 2 seconds before the transaction becomes idle in transaction
        :raises AssertionError: if we wait for more than 2 seconds before the transaction becomes active or locked
        """
        cstr = self.connection_string
        if database is not None:
            cstr["dbname"] = database

        t = PgThread(cstr, query, idle_in_transaction, autocommit)
        t.start()
        if wait_completion:
            # Sometimes we just want too execute a query
            # Threads are useless here but it's quicker to write
            t.join()
        else:
            if idle_in_transaction:
                # We put queries in idle in transaction state to induce locks
                # We have to wait for the status to be correct
                loopcnt = 0
                while not t.is_idle_in_transaction():
                    time.sleep(0.1)
                    loopcnt += 1
                    if loopcnt > 20:
                        raise AssertionError(
                            "Timed out before transaction became idle in transaction"
                        )
                self.idle_in_transaction_threads.append(t)
            else:
                # We at least want to have the query running
                # Sometimes it's not nough and we want the query to be locked
                # The query could also be so short we didn't see it as active
                # It doesn't matter, we will timeout in that case.
                loopcnt = 0
                while (not wait_locked and not t.is_active()) or (
                    wait_locked and not t.is_query_locked()
                ):
                    time.sleep(0.1)
                    loopcnt += 1
                    if loopcnt > 20:
                        raise AssertionError(
                            "Timed out, the transaction is not active or locked"
                        )
                self.others_threads.append(t)

    def cleanup(self: "PgThreadCoord") -> None:
        """wait for all thread to be stopped"""
        # thread idle in transation need to we released before finishing
        for t in self.idle_in_transaction_threads:
            t.stop_idle_in_transactioning()
            t.join()

        # other thread shoud be released because there is no more idle in transaction
        # threads and finish gracefully
        for t in self.others_threads:
            t.join()
