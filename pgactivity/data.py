import getpass
import re
from argparse import Namespace
from typing import Dict, List, Optional, Union

import attr
import psutil
import psycopg2
import psycopg2.extras
from psycopg2 import sql
from psycopg2.errors import (
    InterfaceError,
    InvalidPassword,
    OperationalError,
    ProgrammingError,
)
from psycopg2.extensions import connection

from . import queries
from .types import (
    BlockingProcess,
    Filters,
    WaitingProcess,
    RunningProcess,
    ServerInformation,
    NO_FILTER,
)
from .utils import clean_str


def pg_get_version(pg_conn: connection) -> str:
    """Get PostgreSQL server version."""
    query = queries.get("get_version")
    with pg_conn.cursor() as cur:
        cur.execute(query)
        ret: Dict[str, str] = cur.fetchone()
    return ret["pg_version"]


def pg_get_short_version(text_version: str) -> str:
    """Return PostgreSQL short version from a string (SELECT version()).

    >>> pg_get_short_version('PostgreSQL 11.9')
    'PostgreSQL 11.9'
    >>> pg_get_short_version('EnterpriseDB 11.9 (Debian 11.9-0+deb10u1)')
    'EnterpriseDB 11.9'
    >>> pg_get_short_version("PostgreSQL 9.3.24 on x86_64-pc-linux-gnu (Debian 9.3.24-1.pgdg80+1), compiled by gcc (Debian 4.9.2-10+deb8u1) 4.9.2, 64-bit")
    'PostgreSQL 9.3.24'
    >>> pg_get_short_version("PostgreSQL 9.1.4 on x86_64-unknown-linux-gnu, compiled by gcc (GCC) 4.8.5 20150623 (Red Hat 4.8.5-39), 64-bit")
    'PostgreSQL 9.1.4'
    >>> pg_get_short_version("PostgreSQL 14devel on x86_64-pc-linux-gnu, compiled by gcc (GCC) 9.3.1 20200408 (Red Hat 9.3.1-2), 64-bit")
    'PostgreSQL 14devel'
    >>> pg_get_short_version("PostgreSQL 13beta1 on x86_64-pc-linux-gnu, compiled by gcc (GCC) 9.3.1 20200408 (Red Hat 9.3.1-2), 64-bit")
    'PostgreSQL 13beta1'
    >>> pg_get_short_version("PostgreSQL 13rc1 on x86_64-pc-linux-gnu, compiled by gcc (GCC) 9.3.1 20200408 (Red Hat 9.3.1-2), 64-bit")
    'PostgreSQL 13rc1'
    >>> pg_get_short_version("PostgreSQL 9.6rc1 on x86_64-pc-linux-gnu, compiled by gcc (GCC) 9.3.1 20200408 (Red Hat 9.3.1-2), 64-bit")
    'PostgreSQL 9.6rc1'
    """

    res = re.match(
        r"^\w+ [\d\.]+(devel|beta[0-9]+|rc[0-9]+)?",
        text_version,
    )
    if not res:
        raise Exception(f"Undefined PostgreSQL version: {text_version}")

    return res.group(0)


@attr.s(auto_attribs=True, frozen=True, slots=True)
class Data:
    pg_conn: connection
    pg_version: str
    pg_num_version: int
    min_duration: float
    filters: Filters
    dsn_parameters: Dict[str, str]

    @classmethod
    def pg_connect(
        cls,
        min_duration: float = 0.0,
        *,
        host: Optional[str] = None,
        port: int = 5432,
        user: str = "postgres",
        password: Optional[str] = None,
        database: str = "postgres",
        rds_mode: bool = False,
        dsn: str = "",
        hide_queries_in_logs: bool = False,
        filters: Filters = NO_FILTER,
    ) -> "Data":
        """Create an instance by connecting to a PostgreSQL server."""
        pg_conn = psycopg2.connect(
            dsn=dsn,
            host=host,
            port=port,
            user=user,
            database=database,
            password=password,
            application_name="pg_activity",
            cursor_factory=psycopg2.extras.DictCursor,
        )
        pg_conn.autocommit = True
        with pg_conn.cursor() as cur:
            if hide_queries_in_logs:
                cur.execute(queries.get("disable_log_min_duration_statement"))
                if pg_conn.server_version >= 130000:
                    cur.execute(queries.get("disable_log_min_duration_sample"))
            if not rds_mode:  # Make sure we are using superuser if not on RDS
                cur.execute(queries.get("is_superuser"))
                ret = cur.fetchone()
                if ret[0] != "on":
                    raise Exception("Must be run with database superuser privileges.")
        pg_version = pg_get_short_version(pg_get_version(pg_conn))
        return cls(
            pg_conn,
            pg_version,
            pg_conn.server_version,
            min_duration=min_duration,
            filters=filters,
            dsn_parameters=pg_conn.info.dsn_parameters,
        )

    def try_reconnect(self) -> Optional["Data"]:
        try:
            pg_conn = psycopg2.connect(
                cursor_factory=psycopg2.extras.DictCursor, **self.dsn_parameters
            )
        except (InterfaceError, OperationalError):
            return None
        else:
            pg_conn.autocommit = True
            return attr.evolve(
                self, pg_conn=pg_conn, dsn_parameters=pg_conn.info.dsn_parameters
            )

    def pg_is_local_access(self) -> bool:
        """
        Verify if the user running pg_activity can acces
        system information for the postmaster process.
        """
        try:
            query = queries.get("get_pid_file")
            with self.pg_conn.cursor() as cur:
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
        query = queries.get("do_pg_cancel_backend")
        with self.pg_conn.cursor() as cur:
            cur.execute(query, {"pid": pid})
            ret: Dict[str, bool] = cur.fetchone()
        return ret["is_stopped"]

    def pg_terminate_backend(self, pid: int) -> bool:
        """
        Terminate a backend
        """
        if self.pg_num_version >= 80400:
            query = queries.get("do_pg_terminate_backend")
        else:
            query = queries.get("do_pg_cancel_backend")
        with self.pg_conn.cursor() as cur:
            cur.execute(query, {"pid": pid})
            ret: Dict[str, bool] = cur.fetchone()
        return ret["is_stopped"]

    DbInfoDict = Dict[str, Union[str, int, float]]

    def pg_get_server_information(
        self,
        prev_server_info: Optional[ServerInformation] = None,
        using_rds: bool = False,
        skip_sizes: bool = False,
    ) -> ServerInformation:
        """
        Get the server information (session, workers, cache hit ratio etc..)
        """

        prev_total_size = 0
        if prev_server_info is not None:
            prev_total_size = prev_server_info.total_size

        if self.pg_num_version >= 140000:
            query = queries.get("get_server_info_post_140000")
        elif self.pg_num_version >= 110000:
            query = queries.get("get_server_info_post_110000")
        elif self.pg_num_version >= 100000:
            query = queries.get("get_server_info_post_100000")
        elif self.pg_num_version >= 90600:
            query = queries.get("get_server_info_post_090600")
        elif self.pg_num_version >= 90400:
            query = queries.get("get_server_info_post_090400")
        elif self.pg_num_version >= 90200:
            query = queries.get("get_server_info_post_090200")
        elif self.pg_num_version >= 90000:
            query = queries.get("get_server_info_post_090000")
        else:
            query = queries.get("get_server_info_oldest")

        with self.pg_conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "dbname_filter": self.filters.dbname,
                    "skip_db_size": skip_sizes,
                    "prev_total_size": prev_total_size,
                    "using_rds": using_rds,
                },
            )
            ret = cur.fetchone()

        tps, ips, ups, dps, rps = 0, 0, 0, 0, 0
        size_ev = 0.0
        if prev_server_info is not None:
            dt = float(ret["epoch"] - prev_server_info.epoch)
            try:
                tps = int((ret["xact_count"] - prev_server_info.xact_count) / dt)
                size_ev = float(ret["total_size"] - prev_server_info.total_size) / dt
                ips = int((ret["insert"] - prev_server_info.insert) / dt)
                ups = int((ret["update"] - prev_server_info.update) / dt)
                dps = int((ret["delete"] - prev_server_info.delete) / dt)
                rps = int(
                    (ret["tuples_returned"] - prev_server_info.tuples_returned) / dt
                )
            except ZeroDivisionError:
                pass

        return ServerInformation(
            size_evolution=size_ev,
            tps=tps,
            insert_per_second=ips,
            update_per_second=ups,
            delete_per_second=dps,
            tuples_returned_per_second=rps,
            **ret,
        )

    def pg_get_activities(self, duration_mode: int = 1) -> List[RunningProcess]:
        """
        Get activity from pg_stat_activity view.
        """
        if self.pg_num_version >= 110000:
            qs = queries.get("get_pg_activity_post_110000")
        elif self.pg_num_version >= 100000:
            qs = queries.get("get_pg_activity_post_100000")
        elif self.pg_num_version >= 90600:
            qs = queries.get("get_pg_activity_post_090600")
        elif self.pg_num_version >= 90200:
            qs = queries.get("get_pg_activity_post_090200")
        else:
            qs = queries.get("get_pg_activity_oldest")

        duration_column = self.get_duration_column(duration_mode)
        query = sql.SQL(qs).format(duration_column=sql.Identifier(duration_column))

        with self.pg_conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "min_duration": self.min_duration,
                    "dbname_filter": self.filters.dbname,
                },
            )
            ret = cur.fetchall()

        return [RunningProcess(**row) for row in ret]

    def pg_get_waiting(self, duration_mode: int = 1) -> List[WaitingProcess]:
        """
        Get waiting queries.
        """
        if self.pg_num_version >= 90200:
            qs = queries.get("get_waiting_post_090200")
        else:
            qs = queries.get("get_waiting_oldest")

        duration_column = self.get_duration_column(duration_mode)
        query = sql.SQL(qs).format(duration_column=sql.Identifier(duration_column))

        with self.pg_conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "min_duration": self.min_duration,
                    "dbname_filter": self.filters.dbname,
                },
            )
            ret = cur.fetchall()
        return [WaitingProcess(**row) for row in ret]

    def pg_get_blocking(self, duration_mode: int = 1) -> List[BlockingProcess]:
        """
        Get blocking queries
        """
        if self.pg_num_version >= 90600:
            qs = queries.get("get_blocking_post_090600")
        elif self.pg_num_version >= 90200:
            qs = queries.get("get_blocking_post_090200")
        else:
            qs = queries.get("get_blocking_oldest")

        duration_column = self.get_duration_column(duration_mode)
        query = sql.SQL(qs).format(duration_column=sql.Identifier(duration_column))

        with self.pg_conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "min_duration": self.min_duration,
                    "dbname_filter": self.filters.dbname,
                },
            )
            ret = cur.fetchall()
        return [BlockingProcess(**row) for row in ret]

    def pg_is_local(self) -> bool:
        """
        Is pg_activity connected localy ?
        """
        query = queries.get("get_pga_inet_addresses")
        with self.pg_conn.cursor() as cur:
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
    options: Namespace,
    exit_on_failed: bool = True,
    min_duration: float = 0.0,
    filters: Filters = NO_FILTER,
) -> Data:
    """Try to build a Data instance by to connecting to postgres."""
    password = None
    for nb_try in range(2):
        try:
            data = Data.pg_connect(
                dsn=options.connection_string,
                host=options.host,
                port=options.port,
                user=options.username,
                password=password,
                database=options.dbname,
                rds_mode=options.rds,
                min_duration=min_duration,
                filters=filters,
                hide_queries_in_logs=options.hide_queries_in_logs,
            )
        except OperationalError as err:
            errmsg = str(err).strip()
            if nb_try < 1 and (
                isinstance(err, InvalidPassword)
                or errmsg.startswith("FATAL:  password authentication failed for user")
                or errmsg == "fe_sendauth: no password supplied"
            ):
                password = getpass.getpass()
            elif exit_on_failed:
                msg = str(err).replace("FATAL:", "")
                raise SystemExit("pg_activity: FATAL: %s" % clean_str(msg))
            else:
                raise Exception("Could not connect to PostgreSQL")
        except ProgrammingError as err:
            errmsg = str(err).strip()
            if errmsg.startswith("invalid dsn"):
                raise SystemExit(
                    f"ERROR: {errmsg}\n"
                    "Please refer to the 'Connection Control Functions' section of the PostgreSQL documentation"
                )
            raise
        else:
            break
    return data
