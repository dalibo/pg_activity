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

import psycopg2
import psycopg2.extras
import re
import psutil
import time
from pgactivity.Process import Process
import os
from warnings import catch_warnings, simplefilter

if psutil.version_info < (2, 0, 0):
    class PSProcess(psutil.Process):
        """
        Due to the new psutil 2 API we need to create a new class inherited
        from psutil.Process and wrap old methods.
        """
        def status_iow(self,):
            return str(self.status)

        def io_counters(self,):
            return self.get_io_counters()

        def cpu_time(self,):
            return self.get_cpu_times()

        def memory_info(self,):
            return self.get_memory_info()

        def memory_percent(self,):
            return self.get_memory_percent()

        def cpu_percent(self, interval = 0):
            return self.get_cpu_percent(interval = interval)

        def cpu_times(self,):
            return self.get_cpu_times()
else:
    class PSProcess(psutil.Process):
        def status_iow(self,):
            return str(self.status())

def clean_str(string):
    """
    Strip and replace some special characters.
    """
    msg = str(string)
    msg = msg.replace("\n", " ")
    msg = re.sub(r"\s+", r" ", msg)
    msg = re.sub(r"^\s", r"", msg)
    msg = re.sub(r"\s$", r"", msg)
    return msg

class Data:
    """
    Data class
    """
    pg_conn = None
    pg_version = None
    pg_num_version = None
    io_counters = None
    prev_io_counters = None
    read_bytes_delta = 0
    write_bytes_delta = 0
    read_count_delta = 0
    write_count_delta = 0
    refresh_dbsize = False
    min_duration = 0

    def __init__(self,):
        """
        Constructor.
        """
        self.pg_conn = None
        self.pg_version = None
        self.pg_num_version = None
        self.io_counters = None
        self.prev_io_counters = None
        self.read_bytes_delta = 0
        self.write_bytes_delta = 0
        self.read_count_delta = 0
        self.write_count_delta = 0
        self.refresh_dbsize = False
        self.min_duration = 0

    def get_pg_version(self,):
        """
        Get self.pg_version
        """
        return self.pg_version

    def pg_connect(self,
        host = None,
        port = 5432,
        user = 'postgres',
        password = None,
        database = 'postgres',
        rds_mode = False,
        service = None):
        """
        Connect to a PostgreSQL server and return
        cursor & connector.
        """
        self.pg_conn = None
        if host is None or host == 'localhost':
            # try to connect using UNIX socket
            try:
                if service is not None:
                    self.pg_conn = psycopg2.connect(
                        service = service,
                        connection_factory = psycopg2.extras.DictConnection
                    )
                else:
                    self.pg_conn = psycopg2.connect(
                        database = database,
                        user = user,
                        port = port,
                        password = password,
                        connection_factory = psycopg2.extras.DictConnection
                    )
            except psycopg2.Error as psy_err:
                if host is None:
                    raise psy_err
        if self.pg_conn is None: # fallback on TCP/IP connection
            if service is not None:
                self.pg_conn = psycopg2.connect(
                    service = service,
                    connection_factory = psycopg2.extras.DictConnection
                )
            else:
                self.pg_conn = psycopg2.connect(
                    database = database,
                    host = host,
                    port = port,
                    user = user,
                    password = password,
                    connection_factory = psycopg2.extras.DictConnection
                )
        self.pg_conn.set_isolation_level(0)
        if rds_mode != True: # Make sure we are using superuser if not on RDS
          cur = self.pg_conn.cursor()
          cur.execute("SELECT current_setting('is_superuser')")
          ret = cur.fetchone()
          if ret[0] != "on":
              raise Exception("Must be run with database superuser privileges.")

    def pg_is_local_access(self,):
        """
        Verify if the user running pg_activity can acces
        system informations for the postmaster process.
        """
        try:
            query = "SELECT setting||'/postmaster.pid' AS pid_file FROM pg_settings WHERE name = 'data_directory'"
            cur = self.pg_conn.cursor()
            cur.execute(query)
            ret = cur.fetchone()
            pid_file = ret['pid_file']
            with open(pid_file, 'r') as fd:
                pid = fd.readlines()[0].strip()
                try:
                    proc = PSProcess(int(pid))
                    proc.io_counters()
                    proc.cpu_times()
                    return True
                except psutil.AccessDenied:
                    return False
                except Exception:
                    return False
        except Exception:
            return False

    def pg_get_version(self,):
        """
        Get PostgreSQL server version.
        """
        query = "SELECT version() AS pg_version"
        cur = self.pg_conn.cursor()
        cur.execute(query)
        ret = cur.fetchone()
        return ret['pg_version']

    def pg_cancel_backend(self, pid,):
        """
        Cancel a backend
        """
        query = "SELECT pg_cancel_backend(%s) AS cancelled"
        cur = self.pg_conn.cursor()
        cur.execute(query, (pid,))
        ret = cur.fetchone()
        return ret['cancelled']

    def pg_terminate_backend(self, pid,):
        """
        Terminate a backend
        """
        if self.pg_num_version >= 80400:
            query = "SELECT pg_terminate_backend(%s) AS terminated"
        else:
            query = "SELECT pg_cancel_backend(%s) AS terminated"
        cur = self.pg_conn.cursor()
        cur.execute(query, (pid,))
        ret = cur.fetchone()
        return ret['terminated']

    def pg_get_num_version(self, text_version):
        """
        Get PostgreSQL short & numeric version from
        a string (SELECT version()).
        """
        res = re.match(
                r"^(PostgreSQL|EnterpriseDB) ([0-9]+)\.([0-9]+)(?:\.([0-9]+))?",
                text_version)
        if res is not None:
            rmatch = res.group(2)
            if int(res.group(3)) < 10:
                rmatch += '0'
            rmatch += res.group(3)
            if res.group(4) is not None:
                if int(res.group(4)) < 10:
                    rmatch += '0'
                rmatch += res.group(4)
            else:
                rmatch += '00'
            self.pg_version = str(res.group(0))
            self.pg_num_version = int(rmatch)
            return
        self.pg_get_num_dev_version(text_version)

    def pg_get_num_dev_version(self, text_version):
        """
        Get PostgreSQL short & numeric devel. or beta version
        from a string (SELECT version()).
        """
        res = re.match(
            r"^(PostgreSQL|EnterpriseDB) ([0-9]+)(?:\.([0-9]+))?(devel|beta[0-9]+|rc[0-9]+)",
            text_version)
        if res is not None:
            rmatch = res.group(2)
            if res.group(3) is not None:
                if int(res.group(3)) < 10:
                    rmatch += '0'
                rmatch += res.group(3)
            else:
                rmatch += '00'
            rmatch += '00'
            self.pg_version = str(res.group(0))
            self.pg_num_version = int(rmatch)
            return
        raise Exception('Undefined PostgreSQL version.')

    def pg_get_db_info(self, prev_db_infos, using_rds=False, skip_sizes=False):
        """
        Get current sum of transactions, total size and  timestamp.
        """
        prev_total_size = "0"
        if prev_db_infos is not None:
            prev_total_size = prev_db_infos['total_size']

        skip_dbsize = skip_sizes and (not self.refresh_dbsize)

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
            db_size = prev_total_size if skip_dbsize else "SUM(pg_database_size(datname))",
            no_rds = "WHERE datname <> 'rdsadmin'" if using_rds else ''
        )
        cur = self.pg_conn.cursor()
        cur.execute(query,)
        ret = cur.fetchone()
        tps = 0
        size_ev = 0
        if prev_db_infos is not None:
            tps = int((ret['no_xact'] - prev_db_infos['no_xact'])
                    / (ret['timestamp'] - prev_db_infos['timestamp']))
            size_ev = float(float(ret['total_size']
                        - prev_db_infos['total_size'])
                    / (ret['timestamp'] - prev_db_infos['timestamp']))
        return {
            'timestamp': ret['timestamp'],
            'no_xact': ret['no_xact'],
            'total_size': ret['total_size'],
            'max_length': ret['max_length'],
            'tps': tps,
            'size_ev': size_ev}

    def pg_get_active_connections(self,):
        """
        Get total of active connections.
        """
        query = """
        SELECT
            COUNT(*) as active_connections
        FROM pg_stat_activity
        WHERE state = 'active'
        """

        cur = self.pg_conn.cursor()
        cur.execute(query,)
        ret = cur.fetchone()
        active_connections = int(ret['active_connections'])
        return active_connections

    def pg_get_activities(self, duration_mode=1):
        """
        Get activity from pg_stat_activity view.
        """
        if self.pg_num_version >= 110000:
            # PostgreSQL 11 and more
            query = """
    SELECT
        pg_stat_activity.pid AS pid,
        pg_stat_activity.application_name AS application_name,
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
        pg_stat_activity.application_name AS application_name,
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
        pg_stat_activity.application_name AS application_name,
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
        pg_stat_activity.application_name AS application_name,
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
        '<unknown>' AS application_name,
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
        pg_stat_activity.current_query AS query,
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
        cur.execute(query, {'min_duration': self.min_duration})
        ret = cur.fetchall()

        return ret

    def pg_get_waiting(self, duration_mode=1):
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
        pg_locks.mode AS mode,
        pg_locks.locktype AS type,
        pg_locks.relation::regclass AS relation,
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
        NULL AS state,
        pg_stat_activity.current_query AS query
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
        cur.execute(query, {'min_duration': self.min_duration})
        ret = cur.fetchall()
        return ret

    def pg_get_blocking(self, duration_mode=1):
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
        state,
        relation
    ORDER BY
        duration DESC
            """
        elif self.pg_num_version < 90200:
            query = """
    SELECT
        pid,
        CASE
            WHEN LENGTH(datname) > 16
            THEN SUBSTRING(datname FROM 0 FOR 6)||'...'||SUBSTRING(datname FROM '........$')
            ELSE datname
            END
        AS database,
        usename AS user,
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
            '<unknown>' AS appname,
            pg_stat_activity.current_query AS query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.usename,
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
        state,
        relation
    ORDER BY
        duration DESC
            """

        duration_column = self.get_duration_column(duration_mode)
        query = query.format(duration_column=duration_column)

        cur = self.pg_conn.cursor()
        cur.execute(query, {'min_duration': self.min_duration})
        ret = cur.fetchall()
        return ret

    def pg_is_local(self,):
        """
        Is pg_activity connected localy ?
        """
        query = """
        SELECT inet_server_addr() AS inet_server_addr, inet_client_addr() AS inet_client_addr
        """
        cur = self.pg_conn.cursor()
        cur.execute(query)
        ret = cur.fetchone()
        if ret['inet_server_addr'] == ret['inet_client_addr']:
            return True
        return False

    def get_duration_column(self, duration_mode=1):
        if duration_mode not in (1, 2, 3):
            duration_mode = 1
        return ['query_start', 'xact_start', 'backend_start'][duration_mode-1]

    def get_duration_mode_name(self, duration_mode=1):
        if duration_mode not in (1, 2, 3):
            duration_mode = 1
        return ['query', 'transaction', 'backend'][duration_mode-1]

    def get_duration(self, duration):
        """
        Returns 0 if the given duration is negative
        else, returns the duration
        """
        if duration is None or float(duration) < 0:
            return 0
        return float(duration)

    def __sys_get_iow_status(self, status):
        """
        Returns 'Y' if status == 'disk sleep', else 'N'
        """
        if status == 'disk sleep':
            return 'Y'
        else:
            return 'N'

    def sys_get_proc(self, queries, is_local):
        """
        Get system informations (CPU, memory, IO read & write)
        for each process PID using psutil module.
        """
        processes = {}
        if not is_local:
            return processes
        for query in queries:
            try:
                psproc = PSProcess(query['pid'])
                process = Process(
                    pid = query['pid'],
                    database = query['database'],
                    user = query['user'],
                    client = query['client'],
                    duration = query['duration'],
                    wait = query['wait'],
                    state = query['state'],
                    query = query['query'],
                    extras = {},
                    appname = query['application_name']
                    )

                process.set_extra('meminfo',
                    psproc.memory_info())
                process.set_extra('io_counters',
                    psproc.io_counters())
                process.set_extra('io_time',
                    time.time())
                process.set_extra('mem_percent',
                    psproc.memory_percent())
                process.set_extra('cpu_percent',
                    psproc.cpu_percent(interval=0))
                process.set_extra('cpu_times',
                    psproc.cpu_times())
                process.set_extra('read_delta', 0)
                process.set_extra('write_delta', 0)
                process.set_extra('io_wait',
                    self.__sys_get_iow_status(psproc.status_iow()))
                process.set_extra('psutil_proc', psproc)
                process.set_extra('is_parallel_worker', query['is_parallel_worker'])
                process.set_extra('appname', query['application_name'])

                processes[process.pid] = process

            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                pass
        return processes

    def set_global_io_counters(self,
        read_bytes_delta,
        write_bytes_delta,
        read_count_delta,
        write_count_delta):
        """
        Set IO counters.
        """
        self.read_bytes_delta = read_bytes_delta
        self.write_bytes_delta = write_bytes_delta
        self.read_count_delta = read_count_delta
        self.write_count_delta = write_count_delta

    def get_global_io_counters(self,):
        """
        Get IO counters.
        """
        return {
            'read_bytes': self.read_bytes_delta,
            'write_bytes': self.write_bytes_delta,
            'read_count': self.read_count_delta,
            'write_count': self.write_count_delta}

    def get_mem_swap(self,):
        """
        Get memory and swap usage
        """
        with catch_warnings():
            simplefilter("ignore", RuntimeWarning)
            try:
                # psutil >= 0.6.0
                phymem = psutil.virtual_memory()
                buffers = psutil.virtual_memory().buffers
                cached = psutil.virtual_memory().cached
                vmem = psutil.swap_memory()
            except AttributeError:
                # psutil > 0.4.0 and < 0.6.0
                phymem = psutil.phymem_usage()
                buffers = getattr(psutil, 'phymem_buffers', lambda: 0)()
                cached = getattr(psutil, 'cached_phymem', lambda: 0)()
                vmem = psutil.virtmem_usage()

        mem_used = phymem.total - (phymem.free + buffers + cached)
        return (
            phymem.percent,
            mem_used,
            phymem.total,
            vmem.percent,
            vmem.used,
            vmem.total)

    def get_load_average(self,):
        """
        Get load average
        """
        return os.getloadavg()

    def set_refresh_dbsize(self, refresh_dbsize):
        """
        Set self.refresh_dbsize
        """
        self.refresh_dbsize = refresh_dbsize
