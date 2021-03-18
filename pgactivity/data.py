import getpass
import optparse
import re
from typing import Dict, List, Optional, Tuple, Union

import attr
import psutil
import psycopg2
import psycopg2.extras
from psycopg2.errors import (
    InterfaceError,
    InvalidPassword,
    OperationalError,
    ProgrammingError,
)
from psycopg2.extensions import connection

from . import queries
from .types import BWProcess, RunningProcess
from .utils import clean_str


def pg_get_version(pg_conn: connection) -> str:
    """Get PostgreSQL server version."""
    query = queries.get("get_version")
    with pg_conn.cursor() as cur:
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
    >>> pg_get_num_version("PostgreSQL 9.3.24 on x86_64-pc-linux-gnu (Debian 9.3.24-1.pgdg80+1), compiled by gcc (Debian 4.9.2-10+deb8u1) 4.9.2, 64-bit")
    ('PostgreSQL 9.3.24', 90324)
    >>> pg_get_num_version("PostgreSQL 9.1.24 on x86_64-unknown-linux-gnu, compiled by gcc (GCC) 4.8.5 20150623 (Red Hat 4.8.5-39), 64-bit")
    ('PostgreSQL 9.1.24', 90124)
    >>> pg_get_num_dev_version("PostgreSQL 14devel on x86_64-pc-linux-gnu, compiled by gcc (GCC) 9.3.1 20200408 (Red Hat 9.3.1-2), 64-bit")
    ('PostgreSQL 14devel', 140000)
    >>> pg_get_num_version("PostgreSQL 13beta1 on x86_64-pc-linux-gnu, compiled by gcc (GCC) 9.3.1 20200408 (Red Hat 9.3.1-2), 64-bit")
    ('PostgreSQL 13beta1', 130000)
    >>> pg_get_num_version("PostgreSQL 13rc1 on x86_64-pc-linux-gnu, compiled by gcc (GCC) 9.3.1 20200408 (Red Hat 9.3.1-2), 64-bit")
    ('PostgreSQL 13rc1', 130000)
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

    >>> pg_get_num_dev_version("PostgreSQL 14devel on x86_64-pc-linux-gnu, compiled by gcc (GCC) 9.3.1 20200408 (Red Hat 9.3.1-2), 64-bit")
    ('PostgreSQL 14devel', 140000)
    >>> pg_get_num_version("PostgreSQL 13beta1 on x86_64-pc-linux-gnu, compiled by gcc (GCC) 9.3.1 20200408 (Red Hat 9.3.1-2), 64-bit")
    ('PostgreSQL 13beta1', 130000)
    >>> pg_get_num_version("PostgreSQL 13rc1 on x86_64-pc-linux-gnu, compiled by gcc (GCC) 9.3.1 20200408 (Red Hat 9.3.1-2), 64-bit")
    ('PostgreSQL 13rc1', 130000)
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
    dsn_parameters: Dict[str, str]

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
        dsn: str = "",
        hide_queries_in_logs: bool = False,
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
        pg_version, pg_num_version = pg_get_num_version(pg_get_version(pg_conn))
        return cls(
            pg_conn,
            pg_version,
            pg_num_version,
            min_duration=min_duration,
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
        system informations for the postmaster process.
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
            prev_total_size = prev_db_infos["total_size"]  # type: ignore[assignment]

        query = queries.get("get_db_info")
        with self.pg_conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "skip_db_size": skip_sizes,
                    "prev_total_size": prev_total_size,
                    "using_rds": using_rds,
                },
            )
            ret = cur.fetchone()
        tps = 0
        size_ev = 0.0
        if prev_db_infos is not None:
            try:
                tps = int(
                    (ret["no_xact"] - prev_db_infos["no_xact"])
                    / (ret["timestamp"] - prev_db_infos["timestamp"])
                )
                size_ev = float(
                    float(ret["total_size"] - prev_db_infos["total_size"])
                    / (ret["timestamp"] - prev_db_infos["timestamp"])
                )
            except ZeroDivisionError:
                pass
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
            query = queries.get("get_active_connections")
        else:
            query = queries.get("get_active_connections_post_90200")

        with self.pg_conn.cursor() as cur:
            cur.execute(query)
            ret = cur.fetchone()
        active_connections = int(ret["active_connections"])
        return active_connections

    def pg_get_activities(self, duration_mode: int = 1) -> List[RunningProcess]:
        """
        Get activity from pg_stat_activity view.
        """
        if self.pg_num_version >= 110000:
            query = queries.get("get_pg_activity_post_110000")
        elif self.pg_num_version >= 100000:
            query = queries.get("get_pg_activity_post_100000")
        elif self.pg_num_version >= 90600:
            query = queries.get("get_pg_activity_post_90600")
        elif self.pg_num_version >= 90200:
            query = queries.get("get_pg_activity_post_90200")
        elif self.pg_num_version < 90200:
            query = queries.get("get_pg_activity")

        duration_column = self.get_duration_column(duration_mode)
        query = query.format(duration_column=duration_column)

        with self.pg_conn.cursor() as cur:
            cur.execute(query, {"min_duration": self.min_duration})
            ret = cur.fetchall()

        return [RunningProcess(**row) for row in ret]

    def pg_get_waiting(self, duration_mode: int = 1) -> List[BWProcess]:
        """
        Get waiting queries.
        """
        if self.pg_num_version >= 90200:
            query = queries.get("get_waiting_post_90200")
        elif self.pg_num_version < 90200:
            query = queries.get("get_waiting")

        duration_column = self.get_duration_column(duration_mode)
        query = query.format(duration_column=duration_column)

        with self.pg_conn.cursor() as cur:
            cur.execute(query, {"min_duration": self.min_duration})
            ret = cur.fetchall()
        return [BWProcess(**row) for row in ret]

    def pg_get_blocking(self, duration_mode: int = 1) -> List[BWProcess]:
        """
        Get blocking queries
        """
        if self.pg_num_version >= 90200:
            query = queries.get("get_blocking_post_90200")
        elif self.pg_num_version < 90200:
            query = queries.get("get_blocking")

        duration_column = self.get_duration_column(duration_mode)
        query = query.format(duration_column=duration_column)

        with self.pg_conn.cursor() as cur:
            cur.execute(query, {"min_duration": self.min_duration})
            ret = cur.fetchall()
        return [BWProcess(**row) for row in ret]

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
    options: optparse.Values,
    dsn: str,
    exit_on_failed: bool = True,
    min_duration: float = 0.0,
) -> Data:
    """Try to build a Data instance by to connecting to postgres."""
    password = None
    for nb_try in range(2):
        try:
            data = Data.pg_connect(
                dsn=dsn,
                host=options.host,
                port=options.port,
                user=options.username,
                password=password,
                database=options.dbname,
                rds_mode=options.rds,
                min_duration=min_duration,
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
