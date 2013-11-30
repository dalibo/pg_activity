"""
pg_activity
version: 1.1.0
author: Julien Tachoires <julmon@gmail.com>
license: PostgreSQL License

Copyright (c) 2012 - 2013, Julien Tachoires

Permission to use, copy, modify, and distribute this software and its documentation for any purpose, without fee, and without a written agreement is hereby granted, provided that the above copyright notice and this paragraph and the following two paragraphs appear in all copies.

IN NO EVENT SHALL JULIEN TACHOIRES BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF JULIEN TACHOIRES HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

JULIEN TACHOIRES SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE SOFTWARE PROVIDED HEREUNDER IS ON AN "AS IS" BASIS, AND JULIEN TACHOIRES HAS NO OBLIGATIONS TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
"""

import psycopg2
import psycopg2.extras
import re
import psutil
import time
from Process import *
import os

class Data:

    def __init__(self,):
        """
        Constructor.
        """
        self.pg_conn = None
        self.pg_version = None
        self.pg_num_version = None
        self.io_counters = None
        self.prev_io_counters = None

    def get_pg_version(self,):
        """
        Get self.pg_version
        """
        return self.pg_version

    def clean_str(self, string):
        """
        Strip and replace some special characters.
        """
        msg = str(string)
        msg = msg.replace("\n", " ")
        msg = re.sub(r"\s+", r" ", msg)
        msg = re.sub(r"^\s", r"", msg)
        msg = re.sub(r"\s$", r"", msg)
        return msg

    def get_pgpass(self, pgpass = None):
        """
        Get postgres' password using pgpass file.

        http://www.postgresql.org/docs/9.2/static/libpq-pgpass.html
        http://wiki.postgresql.org/wiki/Pgpass
        """
        if pgpass is None:
            from os.path import expanduser
            home = expanduser("~")
            pgpass = "%s/.pgpass" % (str(home),)
        ret = []
        with open(pgpass, 'r') as fp:
            content = fp.readlines()
            for line in content:
                res = None
                res = re.match(r"^([^:]+):([^:]+):([^:]+):([^:]+):(.*)$", line)
                if res is not None:
                    ret.append(res.group(1, 2, 3, 4, 5))
            return ret
        raise Exception("pgpass file not found")

    def pg_connect(self, host = None, port = 5432, user = 'postgres', password = None, database = 'postgres'):
        """
        Connect to a PostgreSQL server and return
        cursor & connector.
        """
        self.pg_conn = None
        if host is None or host == 'localhost':
            # try to connect using a UNIX Socket by passing host=None
            try:
                self.pg_conn = psycopg2.connect(
                    database = database,
                    user = user,
                    host = None,
                    port = port,
                    password = password,
                    connection_factory=psycopg2.extras.DictConnection
                    )
            except:
                if host is None:
                    raise
        if self.pg_conn is None: # fallback on TCP/IP connection
            self.pg_conn = psycopg2.connect(
                database = database,
                host = host,
                port = port,
                user = user,
                password = str(password),
                connection_factory=psycopg2.extras.DictConnection
                )
        self.pg_conn.set_isolation_level(0)
        cur = self.pg_conn.cursor()
        cur.execute("SELECT current_setting('is_superuser')")
        ret = cur.fetchone()
        if ret[0] != "on":
            raise Exception("Must be run with database superuser privileges.")

    def pg_is_local_access(self,):
        """
        Verify if the user running pg_activity can acces 
        system informations for a postgres process.
        """
        for p in psutil.process_iter():
            if p.name == 'postgres' or p.name == 'postmaster':
                try:
                    proc = psutil.Process(p.pid)
                    proc.get_io_counters()
                    proc.get_cpu_times()
                    return True
                except psutil.AccessDenied:
                    return False
                except Exception:
                    return False
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
        res = re.match(r"^(PostgreSQL|EnterpriseDB) ([0-9]+)\.([0-9]+)\.([0-9]+)", text_version)
        if res is not None:
            r = res.group(2)
            if int(res.group(3)) < 10:
                r += '0'
            r += res.group(3)
            if int(res.group(4)) < 10:
                r += '0'
            r += res.group(4)
            self.pg_version = str(res.group(0))
            self.pg_num_version = int(r)
            return
        self.pg_get_num_dev_version(text_version)

    def pg_get_num_dev_version(self, text_version):
        """
        Get PostgreSQL short & numeric devel. or beta version
        from a string (SELECT version()). 
        """
        res = re.match(r"^(PostgreSQL|EnterpriseDB) ([0-9]+)\.([0-9]+)(devel|beta[0-9]+)", text_version)
        if res is not None:
            r = res.group(2)
            if int(res.group(3)) < 10:
                r += '0'
            r += res.group(3)
            r += '00'
            self.pg_version = str(res.group(0))
            self.pg_num_version = int(r)
            return
        raise Exception('Undefined PostgreSQL version.')

    def pg_get_db_info(self, prev_db_infos):
        """
        Get current sum of transactions, total size and  timestamp.
        """
        query = """
    SELECT
        EXTRACT(EPOCH FROM NOW()) AS timestamp,
        SUM(pg_stat_get_db_xact_commit(oid)+pg_stat_get_db_xact_rollback(oid))::BIGINT AS no_xact,
        SUM(pg_database_size(datname)) AS total_size,
        MAX(LENGTH(datname)) AS max_length
    FROM
        pg_database
        """
        cur = self.pg_conn.cursor()
        cur.execute(query,)
        ret = cur.fetchone()
        tps = 0
        size_ev = 0
        if prev_db_infos is not None:
            tps = int((ret['no_xact'] - prev_db_infos['no_xact']) / (ret['timestamp'] - prev_db_infos['timestamp']))
            size_ev = float(float(ret['total_size'] - prev_db_infos['total_size']) / (ret['timestamp'] - prev_db_infos['timestamp']))
        return {'timestamp':ret['timestamp'], 'no_xact': ret['no_xact'], 'total_size': ret['total_size'], 'max_length': ret['max_length'], 'tps': tps, 'size_ev': size_ev}

    def pg_get_activities(self,):
        """
        Get activity from pg_stat_activity view.
        """
        if self.pg_num_version >= 90200:
            # PostgreSQL 9.2.0 and more
            query = """
    SELECT
        pg_stat_activity.pid AS pid,
        CASE WHEN LENGTH(pg_stat_activity.datname) > 16
            THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
            ELSE pg_stat_activity.datname
            END
        AS database,
        pg_stat_activity.client_addr AS client,
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.query_start)) AS duration,
        pg_stat_activity.waiting AS wait,
        pg_stat_activity.usename AS user,
        pg_stat_activity.query AS query
    FROM
        pg_stat_activity
    WHERE
        state <> 'idle'
        AND pid <> pg_backend_pid()
    ORDER BY
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.query_start)) DESC
            """
        elif self.pg_num_version < 90200:
            # PostgreSQL prior to 9.2.0
            query = """
    SELECT
        pg_stat_activity.procpid AS pid,
        CASE
            WHEN LENGTH(pg_stat_activity.datname) > 16
            THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
            ELSE pg_stat_activity.datname
            END
        AS database,
        pg_stat_activity.client_addr AS client,
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.query_start)) AS duration,
        pg_stat_activity.waiting AS wait,
        pg_stat_activity.usename AS user,
        pg_stat_activity.current_query AS query
    FROM
        pg_stat_activity
    WHERE
        current_query <> '<IDLE>'
        AND procpid <> pg_backend_pid()
    ORDER BY
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.query_start)) DESC
            """
        cur = self.pg_conn.cursor()
        cur.execute(query)
        ret = cur.fetchall()
        return ret

    def pg_get_waiting(self,):
        """
        Get waiting queries.
        """
        if self.pg_num_version >= 90200:
            query = """
    SELECT
        pg_locks.pid AS pid,
        CASE WHEN LENGTH(pg_stat_activity.datname) > 16
            THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
            ELSE pg_stat_activity.datname
            END
        AS database,
        pg_stat_activity.usename AS user,
        pg_locks.mode AS mode,
        pg_locks.locktype AS type,
        pg_locks.relation::regclass AS relation,
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.query_start)) AS duration,
        pg_stat_activity.query AS query
    FROM
        pg_catalog.pg_locks
        JOIN pg_catalog.pg_stat_activity ON(pg_catalog.pg_locks.pid = pg_catalog.pg_stat_activity.pid)
    WHERE
        NOT pg_catalog.pg_locks.granted
        AND pg_catalog.pg_stat_activity.pid <> pg_backend_pid()
    ORDER BY
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.query_start)) DESC
            """
        elif self.pg_num_version < 90200:
            query = """
    SELECT
        pg_locks.pid AS pid,
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
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.query_start)) AS duration,
        pg_stat_activity.current_query AS query
    FROM
        pg_catalog.pg_locks
        JOIN pg_catalog.pg_stat_activity ON(pg_catalog.pg_locks.pid = pg_catalog.pg_stat_activity.procpid)
    WHERE
        NOT pg_catalog.pg_locks.granted
        AND pg_catalog.pg_stat_activity.procpid <> pg_backend_pid()
    ORDER BY
        EXTRACT(epoch FROM (NOW() - pg_stat_activity.query_start)) DESC
            """
        cur = self.pg_conn.cursor()
        cur.execute(query)
        ret = cur.fetchall()
        return ret

    def pg_get_blocking(self,):
        """
        Get blocking queries
        """
        if self.pg_num_version >= 90200:
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
        query
    FROM
        (
        SELECT
            blocking.pid,
            pg_stat_activity.query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.usename,
            blocking.locktype,
            EXTRACT(epoch FROM (NOW() - pg_stat_activity.query_start)) AS duration,
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
        UNION ALL
        SELECT
            blocking.pid,
            pg_stat_activity.query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.usename,
            blocking.locktype,
            EXTRACT(epoch FROM (NOW() - pg_stat_activity.query_start)) AS duration,
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
        ) AS sq
    GROUP BY
        pid,
        query,
        mode,
        locktype,
        duration,
        datname,
        usename,
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
        query
    FROM 
        (
        SELECT
            blocking.pid,
            pg_stat_activity.current_query AS query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.usename,
            blocking.locktype,EXTRACT(epoch FROM (NOW() - pg_stat_activity.query_start)) AS duration,
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
        UNION ALL
        SELECT
            blocking.pid,
            pg_stat_activity.current_query AS query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.usename,
            blocking.locktype,
            EXTRACT(epoch FROM (NOW() - pg_stat_activity.query_start)) AS duration,
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
        ) AS sq
    GROUP BY
        pid,
        query,
        mode,
        locktype,
        duration,
        datname,
        usename,
        relation
    ORDER BY
        duration DESC
            """
        cur = self.pg_conn.cursor()
        cur.execute(query)
        ret = cur.fetchall()
        return ret

    def pg_is_local(self,):
        """
        Is pg_activity connected localy ?
        """
        query = "SELECT inet_server_addr() AS inet_server_addr, inet_client_addr() AS inet_client_addr"
        cur = self.pg_conn.cursor()
        cur.execute(query)
        ret = cur.fetchone()
        if len(str(ret['inet_server_addr'])) == 0 or ret['inet_server_addr'] == ret['inet_client_addr']:
            return True
        return False

    def get_duration(self, duration):
        """
        Returns 0 if the given duration is negative
        else, returns the duration
        """
        if duration is None or float(duration) < 0:
            return 0
        return float(duration)

    def sys_get_IOW_status(self, status):
        """
        Returns 'Y' if status == 'disk sleep', else 'N'
        """
        if str(status) == 'disk sleep':
            return 'Y'
        else:
            return 'N'

    def sys_get_proc(self, queries, is_local):
        """
        Get system informations (CPU, memory, IO read & write)
        for each process PID using psutil module.
        """
        process = {}
        if not is_local:
            return process
        for sq in queries:
            try:
                proc = psutil.Process(sq['pid'])
                p = Process(
                    pid = sq['pid'],
                    database = sq['database'],
                    user = sq['user'],
                    client = sq['client'],
                    duration = sq['duration'],
                    wait = sq['wait'],
                    query = self.clean_str(sq['query']),
                    extras = {}
                    )

                p.setExtra('meminfo',       proc.get_memory_info())
                p.setExtra('io_counters',   proc.get_io_counters())
                p.setExtra('io_time',       time.time())
                p.setExtra('mem_percent',   proc.get_memory_percent())
                p.setExtra('cpu_percent',   proc.get_cpu_percent(interval=0))
                p.setExtra('cpu_times',     proc.get_cpu_times())
                p.setExtra('read_delta',    0)
                p.setExtra('write_delta',   0)
                p.setExtra('io_wait',       self.sys_get_IOW_status(str(proc.status)))
                p.setExtra('psutil_proc',   proc)
                process[p.pid] = p

            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                pass
        return process
 
    def set_global_io_counters(self, read_bytes_delta, write_bytes_delta, read_count_delta, write_count_delta):
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
        return {'read_bytes': self.read_bytes_delta, 'write_bytes': self.write_bytes_delta, 'read_count': self.read_count_delta, 'write_count': self.write_count_delta}

    def get_mem_swap(self,):
        """
        Get memory and swap usage
        """
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
        return (phymem.percent, mem_used, phymem.total, vmem.percent, vmem.used, vmem.total)

    def get_load_average(self,):
        """
        Get load average
        """
        return os.getloadavg()
