"""
pg_activity
author: Julien Tachoires <julmon@gmail.com>
license: PostgreSQL License

Copyright (c) 2012 - 2019, Julien Tachoires
Copyright (c) 2020, Dalibo

Permission to use, copy, modify, and distribute this software and its
documentation for any purpose, without fee, and without a written
agreement is hereby granted, provided that the above copyright notice
and this paragraph and the following two paragraphs appear in all copies.

IN NO EVENT SHALL JULIEN TACHOIRES BE LIABLE TO ANY PARTY FOR DIRECT,
INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST
PROFITS, ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION,
EVEN IF JULIEN TACHOIRES HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

JULIEN TACHOIRES SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT
NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE. THE SOFTWARE PROVIDED HEREUNDER IS ON AN "AS IS"
BASIS, AND JULIEN TACHOIRES HAS NO OBLIGATIONS TO PROVIDE MAINTENANCE,
SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
"""

import getpass
import optparse
import re
from typing import Dict, List, Optional, Tuple, Union

import attr
import psutil
import psycopg2
import psycopg2.extras
from psycopg2 import errorcodes
from psycopg2.extensions import connection

from .types import BWProcess, RunningProcess
from .utils import clean_str


def pg_get_version(pg_conn: connection) -> str:
    """Get PostgreSQL server version."""
    query = "SELECT version() AS pg_version"
    cur = pg_conn.cursor()
    cur.execute(query)
    ret: Dict[str, str] = cur.fetchone()
    return ret["pg_version"]


def pg_get_num_version(text_version: str) -> Tuple[str, int]:
    """Return PostgreSQL short & numeric version from a string (SELECT
    version()).

    >>> pg_get_num_version('PostgreSQL 11.9')
    ('PostgreSQL 11.9', 110900)
    >>> pg_get_num_version('EnterpriseDB 11.9 (Debian 11.9-0+deb10u1)')
    ('EnterpriseDB 11.9', 110900)
    >>> pg_get_num_version("PostgreSQL 13.0beta2")
    ('PostgreSQL 13.0', 130000)
    """
    res = re.match(
        r"^(PostgreSQL|EnterpriseDB) ([0-9]+)\.([0-9]+)(?:\.([0-9]+))?",
        text_version,
    )
    if res is not None:
        rmatch = res.group(2)
        if int(res.group(3)) < 10:
            rmatch += "0"
        rmatch += res.group(3)
        if res.group(4) is not None:
            if int(res.group(4)) < 10:
                rmatch += "0"
            rmatch += res.group(4)
        else:
            rmatch += "00"
        pg_version = str(res.group(0))
        pg_num_version = int(rmatch)
        return pg_version, pg_num_version
    return pg_get_num_dev_version(text_version)


def pg_get_num_dev_version(text_version: str) -> Tuple[str, int]:
    """Return PostgreSQL short & numeric devel. or beta version from a string
    (SELECT version()).

    >>> pg_get_num_dev_version("PostgreSQL 11.9devel0")
    ('PostgreSQL 11.9devel', 110900)
    """
    res = re.match(
        r"^(PostgreSQL|EnterpriseDB) ([0-9]+)(?:\.([0-9]+))?(devel|beta[0-9]+|rc[0-9]+)",
        text_version,
    )
    if not res:
        raise Exception(f"Undefined PostgreSQL version: {text_version}")
    rmatch = res.group(2)
    if res.group(3) is not None:
        if int(res.group(3)) < 10:
            rmatch += "0"
        rmatch += res.group(3)
    else:
        rmatch += "00"
    rmatch += "00"
    pg_version = str(res.group(0))
    pg_num_version = int(rmatch)
    return pg_version, pg_num_version


@attr.s(auto_attribs=True, frozen=True, slots=True)
class Data:
    pg_conn: connection
    pg_version: str
    pg_num_version: int
    min_duration: float

    @classmethod
    def pg_connect(
        cls,
        min_duration: float,
        *,
        host: Optional[str] = None,
        port: int = 5432,
        user: str = "postgres",
        password: Optional[str] = None,
        database: str = "postgres",
        rds_mode: bool = False,
        service: Optional[str] = None,
    ) -> "Data":
        """Create an instance by connecting to a PostgreSQL server."""
        pg_conn = None
        if host is None or host == "localhost":
            # try to connect using UNIX socket
            try:
                if service is not None:
                    pg_conn = psycopg2.connect(
                        service=service,
                        cursor_factory=psycopg2.extras.DictCursor,
                    )
                else:
                    pg_conn = psycopg2.connect(
                        database=database,
                        user=user,
                        port=port,
                        password=password,
                        cursor_factory=psycopg2.extras.DictCursor,
                    )
            except psycopg2.Error as psy_err:
                if host is None:
                    raise psy_err
        if pg_conn is None:  # fallback on TCP/IP connection
            if service is not None:
                pg_conn = psycopg2.connect(
                    service=service,
                    cursor_factory=psycopg2.extras.DictCursor,
                )
            else:
                pg_conn = psycopg2.connect(
                    database=database,
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    cursor_factory=psycopg2.extras.DictCursor,
                )
        pg_conn.set_isolation_level(0)
        if not rds_mode:  # Make sure we are using superuser if not on RDS
            cur = pg_conn.cursor()
            cur.execute("SELECT current_setting('is_superuser')")
            ret = cur.fetchone()
            if ret[0] != "on":
                raise Exception("Must be run with database superuser privileges.")
        pg_version, pg_num_version = pg_get_num_version(pg_get_version(pg_conn))
        return cls(pg_conn, pg_version, pg_num_version, min_duration=min_duration)

    def pg_is_local_access(self) -> bool:
        """
        Verify if the user running pg_activity can acces
        system informations for the postmaster process.
        """
        try:
            query = "SELECT setting||'/postmaster.pid' AS pid_file FROM pg_settings WHERE name = 'data_directory'"
            cur = self.pg_conn.cursor()
            cur.execute(query)
            ret = cur.fetchone()
            pid_file = ret["pid_file"]
            with open(pid_file, "r") as fd:
                pid = fd.readlines()[0].strip()
                try:
                    proc = psutil.Process(int(pid))
                    proc.io_counters()
                    proc.cpu_times()
                    return True
                except psutil.AccessDenied:
                    return False
                except Exception:
                    return False
        except Exception:
            return False

    def pg_cancel_backend(self, pid: int) -> bool:
        """
        Cancel a backend
        """
        query = "SELECT pg_cancel_backend(%s) AS cancelled"
        cur = self.pg_conn.cursor()
        cur.execute(query, (pid,))
        ret: Dict[str, bool] = cur.fetchone()
        return ret["cancelled"]

    def pg_terminate_backend(self, pid: int) -> bool:
        """
        Terminate a backend
        """
        if self.pg_num_version >= 80400:
            query = "SELECT pg_terminate_backend(%s) AS terminated"
        else:
            query = "SELECT pg_cancel_backend(%s) AS terminated"
        cur = self.pg_conn.cursor()
        cur.execute(query, (pid,))
        ret: Dict[str, bool] = cur.fetchone()
        return ret["terminated"]

    DbInfoDict = Dict[str, Union[str, int, float]]

    def pg_get_db_info(
        self,
        prev_db_infos: Optional[DbInfoDict],
        using_rds: bool = False,
        skip_sizes: bool = False,
    ) -> DbInfoDict:
        """
        Get current sum of transactions, total size and  timestamp.
        """
        prev_total_size = "0"
        if prev_db_infos is not None:
            prev_total_size = prev_db_infos["total_size"]  # type: ignore

        skip_dbsize = skip_sizes

        query = """
    SELECT
        EXTRACT(EPOCH FROM NOW()) AS timestamp,
        SUM(pg_stat_get_db_xact_commit(oid)+pg_stat_get_db_xact_rollback(oid))::BIGINT AS no_xact,
        {db_size} AS total_size,
        MAX(LENGTH(datname)) AS max_length
    FROM
        pg_database
        {no_rds}
        """.format(
            db_size=prev_total_size
            if skip_dbsize
            else "SUM(pg_database_size(datname))",
            no_rds="WHERE datname <> 'rdsadmin'" if using_rds else "",
        )
        cur = self.pg_conn.cursor()
        cur.execute(
            query,
        )
        ret = cur.fetchone()
        tps = 0
        size_ev = 0.0
        if prev_db_infos is not None:
            tps = int(
                (ret["no_xact"] - prev_db_infos["no_xact"])
                / (ret["timestamp"] - prev_db_infos["timestamp"])
            )
            size_ev = float(
                float(ret["total_size"] - prev_db_infos["total_size"])
                / (ret["timestamp"] - prev_db_infos["timestamp"])
            )
        return {
            "timestamp": ret["timestamp"],
            "no_xact": ret["no_xact"],
            "total_size": ret["total_size"],
            "max_length": ret["max_length"],
            "tps": tps,
            "size_ev": size_ev,
        }

    def pg_get_active_connections(self) -> int:
        """
        Get total of active connections.
        """

        if self.pg_num_version < 90200:
            # prior to PostgreSQL 9.1, there was no state column
            query = """
    SELECT
        COUNT(*) as active_connections
    FROM pg_stat_activity
    WHERE current_query NOT LIKE '<IDLE>%%'
            """
        else:
            query = """
    SELECT
        COUNT(*) as active_connections
    FROM pg_stat_activity
    WHERE state = 'active'
            """

        cur = self.pg_conn.cursor()
        cur.execute(query)
        ret = cur.fetchone()
        active_connections = int(ret["active_connections"])
        return active_connections

    def pg_get_activities(self, duration_mode: int = 1) -> List[RunningProcess]:
        """
        Get activity from pg_stat_activity view.
        """
        if self.pg_num_version >= 110000:
            # PostgreSQL 11 and more
            query = """
    SELECT
        pg_stat_activity.pid AS pid,
        pg_stat_activity.application_name AS appname,
        CASE WHEN LENGTH(pg_stat_activity.datname) > 16
            THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
            ELSE pg_stat_activity.datname
            END
        AS database,
        CASE WHEN pg_stat_activity.client_addr IS NULL
            THEN 'local'
            ELSE pg_stat_activity.client_addr::TEXT
            END
        AS client,
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
        CASE WHEN pg_stat_activity.wait_event_type IN ('LWLock', 'Lock', 'BufferPin') THEN true ELSE false END AS wait,
        pg_stat_activity.usename AS user,
        pg_stat_activity.state AS state,
        pg_stat_activity.query AS query,
        pg_stat_activity.backend_type = 'parallel worker' AS is_parallel_worker
    FROM
        pg_stat_activity
    WHERE
        state <> 'idle'
        AND pid <> pg_backend_pid()
        AND CASE WHEN %(min_duration)s = 0 THEN true
            ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
            END
    ORDER BY
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC
            """
        elif self.pg_num_version >= 100000:
            # PostgreSQL 10
            # We assume a background_worker with a not null query is a parallel worker.
            query = """
    SELECT
        pg_stat_activity.pid AS pid,
        pg_stat_activity.application_name AS appname,
        CASE WHEN LENGTH(pg_stat_activity.datname) > 16
            THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
            ELSE pg_stat_activity.datname
            END
        AS database,
        CASE WHEN pg_stat_activity.client_addr IS NULL
            THEN 'local'
            ELSE pg_stat_activity.client_addr::TEXT
            END
        AS client,
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
        CASE WHEN pg_stat_activity.wait_event_type IN ('LWLock', 'Lock', 'BufferPin') THEN true ELSE false END AS wait,
        pg_stat_activity.usename AS user,
        pg_stat_activity.state AS state,
        pg_stat_activity.query AS query,
        (pg_stat_activity.backend_type = 'background worker' AND pg_stat_activity.query IS NOT NULL) AS is_parallel_worker
    FROM
        pg_stat_activity
    WHERE
        state <> 'idle'
        AND pid <> pg_backend_pid()
        AND CASE WHEN %(min_duration)s = 0 THEN true
            ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
            END
    ORDER BY
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC
            """
        elif self.pg_num_version >= 90600:
            # PostgreSQL prior to 10.0 and >= 9.6.0
            # There is no way to see parallel workers
            query = """
    SELECT
        pg_stat_activity.pid AS pid,
        pg_stat_activity.application_name AS appname,
        CASE WHEN LENGTH(pg_stat_activity.datname) > 16
            THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
            ELSE pg_stat_activity.datname
            END
        AS database,
        CASE WHEN pg_stat_activity.client_addr IS NULL
            THEN 'local'
            ELSE pg_stat_activity.client_addr::TEXT
            END
        AS client,
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
        pg_stat_activity.wait_event IS NOT NULL AS wait,
        pg_stat_activity.usename AS user,
        pg_stat_activity.state AS state,
        pg_stat_activity.query AS query,
        false AS is_parallel_worker
    FROM
        pg_stat_activity
    WHERE
        state <> 'idle'
        AND pid <> pg_backend_pid()
        AND CASE WHEN %(min_duration)s = 0 THEN true
            ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
            END
    ORDER BY
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC
            """
        elif self.pg_num_version >= 90200:
            # PostgreSQL prior to 9.6.0 and >= 9.2.0
            query = """
    SELECT
        pg_stat_activity.pid AS pid,
        pg_stat_activity.application_name AS appname,
        CASE WHEN LENGTH(pg_stat_activity.datname) > 16
            THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
            ELSE pg_stat_activity.datname
            END
        AS database,
        CASE WHEN pg_stat_activity.client_addr IS NULL
            THEN 'local'
            ELSE pg_stat_activity.client_addr::TEXT
            END
        AS client,
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
        pg_stat_activity.waiting AS wait,
        pg_stat_activity.usename AS user,
        pg_stat_activity.state AS state,
        pg_stat_activity.query AS query,
        false AS is_parallel_worker
    FROM
        pg_stat_activity
    WHERE
        state <> 'idle'
        AND pid <> pg_backend_pid()
        AND CASE WHEN %(min_duration)s = 0 THEN true
            ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
            END
    ORDER BY
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC
            """
        elif self.pg_num_version < 90200:
            # PostgreSQL prior to 9.2.0
            query = """
    SELECT
        pg_stat_activity.procpid AS pid,
        '<unknown>' AS appname,
        CASE
            WHEN LENGTH(pg_stat_activity.datname) > 16
            THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
            ELSE pg_stat_activity.datname
            END
        AS database,
        CASE WHEN pg_stat_activity.client_addr IS NULL
            THEN 'local'
            ELSE pg_stat_activity.client_addr::TEXT
            END
        AS client,
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
        pg_stat_activity.waiting AS wait,
        pg_stat_activity.usename AS user,
        CASE
            WHEN pg_stat_activity.current_query = '<IDLE> in transaction (aborted)' THEN 'idle in transaction (aborted)'
            WHEN pg_stat_activity.current_query = '<IDLE> in transaction' THEN 'idle in transaction'
            WHEN pg_stat_activity.current_query = '<IDLE>' THEN 'idle'
            ELSE 'active'
            END
        AS state,
        CASE
           WHEN pg_stat_activity.current_query LIKE '<IDLE>%%' THEN 'None'
           ELSE pg_stat_activity.current_query
           END
        AS query,
        false AS is_parallel_worker
    FROM
        pg_stat_activity
    WHERE
        current_query <> '<IDLE>'
        AND procpid <> pg_backend_pid()
        AND CASE WHEN %(min_duration)s = 0 THEN true
            ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
            END
    ORDER BY
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC
            """

        duration_column = self.get_duration_column(duration_mode)
        query = query.format(duration_column=duration_column)

        cur = self.pg_conn.cursor()
        cur.execute(query, {"min_duration": self.min_duration})
        ret = cur.fetchall()

        return [RunningProcess(**row) for row in ret]

    def pg_get_waiting(self, duration_mode: int = 1) -> List[BWProcess]:
        """
        Get waiting queries.
        """
        if self.pg_num_version >= 90200:
            query = """
    SELECT
        pg_locks.pid AS pid,
        pg_stat_activity.application_name AS appname,
        CASE WHEN LENGTH(pg_stat_activity.datname) > 16
            THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
            ELSE pg_stat_activity.datname
            END
        AS database,
        pg_stat_activity.usename AS user,
        CASE WHEN pg_stat_activity.client_addr IS NULL
            THEN 'local'
            ELSE pg_stat_activity.client_addr::TEXT
            END
        AS client,
        pg_locks.mode AS mode,
        pg_locks.locktype AS type,
        pg_locks.relation::regclass AS relation,
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
        pg_stat_activity.state as state,
        pg_stat_activity.query AS query
    FROM
        pg_catalog.pg_locks
        JOIN pg_catalog.pg_stat_activity ON(pg_catalog.pg_locks.pid = pg_catalog.pg_stat_activity.pid)
    WHERE
        NOT pg_catalog.pg_locks.granted
        AND pg_catalog.pg_stat_activity.pid <> pg_backend_pid()
        AND CASE WHEN %(min_duration)s = 0 THEN true
            ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
            END
    ORDER BY
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC
            """
        elif self.pg_num_version < 90200:
            query = """
    SELECT
        pg_locks.pid AS pid,
        '<unknown>' AS appname,
        CASE
            WHEN LENGTH(pg_stat_activity.datname) > 16
            THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
            ELSE pg_stat_activity.datname
            END
        AS database,
        pg_stat_activity.usename AS user,
        CASE WHEN pg_stat_activity.client_addr IS NULL
            THEN 'local'
            ELSE pg_stat_activity.client_addr::TEXT
            END
        AS client,
        pg_locks.mode AS mode,
        pg_locks.locktype AS type,
        pg_locks.relation::regclass AS relation,
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
        CASE
           WHEN pg_stat_activity.current_query = '<IDLE> in transaction (aborted)' THEN 'idle in transaction (aborted)'
           WHEN pg_stat_activity.current_query = '<IDLE> in transaction' THEN 'idle in transaction'
           WHEN pg_stat_activity.current_query = '<IDLE>' THEN 'idle'
           ELSE 'active'
           END
        AS state,
        CASE
           WHEN pg_stat_activity.current_query LIKE '<IDLE>%%' THEN 'None'
           ELSE pg_stat_activity.current_query
           END
        AS query
    FROM
        pg_catalog.pg_locks
        JOIN pg_catalog.pg_stat_activity ON(pg_catalog.pg_locks.pid = pg_catalog.pg_stat_activity.procpid)
    WHERE
        NOT pg_catalog.pg_locks.granted
        AND pg_catalog.pg_stat_activity.procpid <> pg_backend_pid()
        AND CASE WHEN %(min_duration)s = 0 THEN true
            ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
            END
    ORDER BY
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC
            """

        duration_column = self.get_duration_column(duration_mode)
        query = query.format(duration_column=duration_column)

        cur = self.pg_conn.cursor()
        cur.execute(query, {"min_duration": self.min_duration})
        ret = cur.fetchall()
        return [BWProcess(**row) for row in ret]

    def pg_get_blocking(self, duration_mode: int = 1) -> List[BWProcess]:
        """
        Get blocking queries
        """
        if self.pg_num_version >= 90200:
            query = """
    SELECT
        pid,
        application_name AS appname,
        CASE
            WHEN LENGTH(datname) > 16
            THEN SUBSTRING(datname FROM 0 FOR 6)||'...'||SUBSTRING(datname FROM '........$')
            ELSE datname
            END
        AS database,
        usename AS user,
        client,
        relation,
        mode,
        locktype AS type,
        duration,
        state,
        query
    FROM
        (
        SELECT
            blocking.pid,
            pg_stat_activity.application_name,
            pg_stat_activity.query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.usename,
            CASE WHEN pg_stat_activity.client_addr IS NULL
                THEN 'local'
                ELSE pg_stat_activity.client_addr::TEXT
                END
            AS client,
            blocking.locktype,
            EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
            pg_stat_activity.state as state,
            blocking.relation::regclass AS relation
        FROM
            pg_locks AS blocking
            JOIN (
                SELECT
                    transactionid
                FROM
                    pg_locks
                WHERE
                    NOT granted) AS blocked ON (blocking.transactionid = blocked.transactionid)
            JOIN pg_stat_activity ON (blocking.pid = pg_stat_activity.pid)
        WHERE
            blocking.granted
            AND CASE WHEN %(min_duration)s = 0 THEN true
                ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
                END
        UNION ALL
        SELECT
            blocking.pid,
            pg_stat_activity.application_name,
            pg_stat_activity.query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.usename,
            CASE WHEN pg_stat_activity.client_addr IS NULL
                THEN 'local'
                ELSE pg_stat_activity.client_addr::TEXT
                END
            AS client,
            blocking.locktype,
            EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
            pg_stat_activity.state as state,
            blocking.relation::regclass AS relation
        FROM
            pg_locks AS blocking
            JOIN (
                SELECT
                    database,
                    relation,
                    mode
                FROM
                    pg_locks
                WHERE
                    NOT granted
                    AND relation IS NOT NULL) AS blocked ON (blocking.database = blocked.database AND blocking.relation = blocked.relation)
            JOIN pg_stat_activity ON (blocking.pid = pg_stat_activity.pid)
        WHERE
            blocking.granted
            AND CASE WHEN %(min_duration)s = 0 THEN true
                ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
                END
        ) AS sq
    GROUP BY
        pid,
        application_name,
        query,
        mode,
        locktype,
        duration,
        datname,
        usename,
        client,
        state,
        relation
    ORDER BY
        duration DESC
            """
        elif self.pg_num_version < 90200:
            query = """
    SELECT
        pid,
        appname,
        CASE
            WHEN LENGTH(datname) > 16
            THEN SUBSTRING(datname FROM 0 FOR 6)||'...'||SUBSTRING(datname FROM '........$')
            ELSE datname
            END
        AS database,
        usename AS user,
        client,
        relation,
        mode,
        locktype AS type,
        duration,
        CASE
           WHEN sq.query = '<IDLE> in transaction (aborted)' THEN 'idle in transaction (aborted)'
           WHEN sq.query = '<IDLE> in transaction' THEN 'idle in transaction'
           WHEN sq.query = '<IDLE>' THEN 'idle'
           ELSE 'active'
           END
        AS state,
        CASE
           WHEN sq.query LIKE '<IDLE>%%' THEN 'None'
           ELSE sq.query
           END
        AS query
    FROM
        (
        SELECT
            blocking.pid,
            '<unknown>' AS appname,
            pg_stat_activity.current_query AS query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.usename,
            CASE WHEN pg_stat_activity.client_addr IS NULL
                THEN 'local'
                ELSE pg_stat_activity.client_addr::TEXT
                END
            AS client,
            blocking.locktype,EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
            NULL AS state,
            blocking.relation::regclass AS relation
        FROM
            pg_locks AS blocking
            JOIN (
                SELECT
                    transactionid
                FROM
                    pg_locks
                WHERE
                    NOT granted) AS blocked ON (blocking.transactionid = blocked.transactionid)
            JOIN pg_stat_activity ON (blocking.pid = pg_stat_activity.procpid)
        WHERE
            blocking.granted
            AND CASE WHEN %(min_duration)s = 0 THEN true
                ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
                END
        UNION ALL
        SELECT
            blocking.pid,
            '<unknown>' AS appname,
            pg_stat_activity.current_query AS query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.usename,
            CASE WHEN pg_stat_activity.client_addr IS NULL
                THEN 'local'
                ELSE pg_stat_activity.client_addr::TEXT
                END
            AS client,
            blocking.locktype,
            EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
            NULL AS state,
            blocking.relation::regclass AS relation
        FROM
            pg_locks AS blocking
            JOIN (
                SELECT
                    database,
                    relation,
                    mode
                FROM
                    pg_locks
                WHERE
                    NOT granted
                    AND relation IS NOT NULL) AS blocked ON (blocking.database = blocked.database AND blocking.relation = blocked.relation)
            JOIN pg_stat_activity ON (blocking.pid = pg_stat_activity.procpid)
        WHERE
            blocking.granted
            AND CASE WHEN %(min_duration)s = 0 THEN true
                ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
                END
        ) AS sq
    GROUP BY
        pid,
        appname,
        query,
        mode,
        locktype,
        duration,
        datname,
        usename,
        client,
        state,
        relation
    ORDER BY
        duration DESC
            """

        duration_column = self.get_duration_column(duration_mode)
        query = query.format(duration_column=duration_column)

        cur = self.pg_conn.cursor()
        cur.execute(query, {"min_duration": self.min_duration})
        ret = cur.fetchall()
        return [BWProcess(**row) for row in ret]

    def pg_is_local(self) -> bool:
        """
        Is pg_activity connected localy ?
        """
        query = """
        SELECT inet_server_addr() AS inet_server_addr, inet_client_addr() AS inet_client_addr
        """
        cur = self.pg_conn.cursor()
        cur.execute(query)
        ret = cur.fetchone()
        if ret["inet_server_addr"] == ret["inet_client_addr"]:
            return True
        return False

    @staticmethod
    def get_duration_column(duration_mode: int = 1) -> str:
        """Return the duration column depending on duration_mode.

        >>> Data.get_duration_column(1)
        'query_start'
        >>> Data.get_duration_column(2)
        'xact_start'
        >>> Data.get_duration_column(3)
        'backend_start'
        >>> Data.get_duration_column(9)
        'query_start'
        """
        if duration_mode not in (1, 2, 3):
            duration_mode = 1
        return ["query_start", "xact_start", "backend_start"][duration_mode - 1]


def pg_connect(
    options: optparse.Values,
    password: Optional[str] = None,
    service: Optional[str] = None,
    exit_on_failed: bool = True,
    min_duration: float = 0.0,
) -> Data:
    """Try to build a Data instance by to connecting to postgres."""
    for nb_try in range(2):
        try:
            data = Data.pg_connect(
                host=options.host,
                port=options.port,
                user=options.username,
                password=password,
                database=options.dbname,
                rds_mode=options.rds,
                service=service,
                min_duration=min_duration,
            )
        except psycopg2.OperationalError as err:
            errmsg = str(err).strip()
            if nb_try < 1 and (
                err.pgcode == errorcodes.INVALID_PASSWORD
                or errmsg.startswith("FATAL:  password authentication failed for user")
                or errmsg == "fe_sendauth: no password supplied"
            ):
                password = getpass.getpass()
            elif exit_on_failed:
                msg = str(err).replace("FATAL:", "")
                raise SystemExit("pg_activity: FATAL: %s" % clean_str(msg))
            else:
                raise Exception("Could not connect to PostgreSQL")
        else:
            break
    return data
