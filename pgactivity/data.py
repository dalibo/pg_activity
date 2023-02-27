import getpass
import logging
import re
from argparse import Namespace
from functools import partial
from typing import Dict, List, Optional

import attr
import psutil

from . import queries, pg
from .pg import sql, Connection
from .types import (
    BlockingProcess,
    FailedQueriesInfo,
    Filters,
    WaitingProcess,
    Pct,
    RunningProcess,
    ServerInformation,
    TempFileInfo,
    NO_FILTER,
)
from .utils import clean_str


logger = logging.getLogger("pgactivity")


def pg_get_version(pg_conn: Connection) -> str:
    """Get PostgreSQL server version."""
    ret = pg.fetchone(pg_conn, queries.get("get_version"))
    return ret["pg_version"]  # type: ignore[no-any-return]


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
    pg_conn: Connection
    pg_version: str
    pg_num_version: int
    server_encoding: str
    min_duration: float
    filters: Filters
    dsn_parameters: Dict[str, str]
    failed_queries: FailedQueriesInfo

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
        pg_conn = pg.connect(
            dsn,
            host=host,
            port=port,
            user=user,
            dbname=database,
            password=password,
            application_name="pg_activity",
        )
        if hide_queries_in_logs:
            pg.execute(pg_conn, queries.get("disable_log_min_duration_statement"))
            if pg.server_version(pg_conn) >= 130000:
                pg.execute(pg_conn, queries.get("disable_log_min_duration_sample"))
        pg_version = pg_get_short_version(pg_get_version(pg_conn))
        server_encoding = pg_conn.info.parameter_status("server_encoding")
        assert server_encoding is not None
        return cls(
            pg_conn,
            pg_version,
            pg.server_version(pg_conn),
            server_encoding,
            min_duration=min_duration,
            failed_queries=FailedQueriesInfo(),
            filters=filters,
            dsn_parameters=pg.connection_parameters(pg_conn),
        )

    def try_reconnect(self) -> Optional["Data"]:
        try:
            pg_conn = pg.connect(**self.dsn_parameters)
        except (pg.InterfaceError, pg.OperationalError):
            return None
        else:
            return attr.evolve(
                self, pg_conn=pg_conn, dsn_parameters=pg.connection_parameters(pg_conn)
            )

    def pg_is_local_access(self) -> bool:
        """
        Verify if the user running pg_activity can access
        system information for the postmaster process.
        """
        query = queries.get("get_data_directory")
        try:
            ret = pg.fetchone(self.pg_conn, query)
        except pg.InsufficientPrivilege:
            logger.info(
                "Insufficient privilege to show data_directory. System counters are disabled."
            )
            return False

        pid_file = f"{ret['data_directory']}/postmaster.pid"
        try:
            with open(pid_file, "r") as fd:
                pid = fd.readline().strip()
        except OSError as e:
            logger.info(
                "pidfile %s could not be read: %s. System counters are disabled.",
                pid_file,
                e,
            )
            return False

        try:
            proc = psutil.Process(int(pid))
            proc.io_counters()
            proc.cpu_times()
            return True
        except psutil.AccessDenied:
            logger.info(
                "Access denied to the psutil data. System counters are disabled."
            )
            return False
        except AttributeError:
            # See issue #300
            logger.info(
                "Your platform doesn't support some of psutil features required to get system counters. "
                "System counters are disabled."
            )
            return False

    def pg_cancel_backend(self, pid: int) -> bool:
        """
        Cancel a backend
        """
        query = queries.get("do_pg_cancel_backend")
        ret = pg.fetchone(self.pg_conn, query, {"pid": pid})
        return ret["is_stopped"]  # type: ignore[no-any-return]

    def pg_terminate_backend(self, pid: int) -> bool:
        """
        Terminate a backend
        """
        if self.pg_num_version >= 80400:
            query = queries.get("do_pg_terminate_backend")
        else:
            query = queries.get("do_pg_cancel_backend")
        ret = pg.fetchone(self.pg_conn, query, {"pid": pid})
        return ret["is_stopped"]  # type: ignore[no-any-return]

    def pg_get_temporary_file(self) -> Optional[TempFileInfo]:
        """
        Count the number of temporary files and get their total size
        """
        if self.failed_queries.temp_file_query_failed:
            # prevent a spam of errors in PostgreSQL logs if we already failed once
            # for lack of privilege or timeout
            return None

        if self.pg_num_version >= 120000:
            query = queries.get("get_temporary_files_post_120000")
        elif self.pg_num_version >= 90100:
            query = queries.get("get_temporary_files_post_090100")
        else:
            query = queries.get("get_temporary_files_oldest")

        try:
            pg.execute(
                self.pg_conn,
                sql.SQL("SET statement_timeout TO {}").format(sql.Literal("400ms")),
            )
            return pg.fetchone(self.pg_conn, query, mkrow=TempFileInfo)
        except pg.InsufficientPrivilege:
            # superuser or pg_read_server_files are required (Issue #278)
            self.failed_queries.temp_file_query_failed = True
            logger.info(
                "Insufficient privilege to fetch the tempfile data. "
                "The feature was disabled. Please use --no-tempfiles or a platform specific setting (eg. --rds)."
            )

            return None
        except pg.QueryCanceled:
            # if an excessive amount of tempfile exists, the query could be very long
            # to avoid such a case we set a statement_timeout shorter than the lowest
            # refresh rate. This could end up spamming the PostgreSQL logs.
            self.failed_queries.temp_file_query_failed = True
            logger.info(
                "The tempfile query ended in a timeout. "
                "The feature was disabled. Check the temporary files on the server."
            )
            return None
        finally:
            pg.execute(self.pg_conn, queries.get("reset_statement_timeout"))

    def pg_get_wal_senders(self) -> Optional[int]:
        """
        Count the number of wal senders
        """
        if self.pg_num_version >= 90100:
            query = queries.get("get_wal_senders_post_090100")
        else:
            return None
        ret = pg.fetchone(self.pg_conn, query)
        return int(ret["wal_senders"])

    def pg_get_wal_receivers(self) -> Optional[int]:
        """
        Count the number of wal receivers
        """
        if self.failed_queries.wal_receivers_query_failed:
            # prevent a spam of errors un PostgreSQL logs if we already failed once
            # because the feature is not implemented
            return None

        if self.pg_num_version >= 90600:
            query = queries.get("get_wal_receivers_post_090600")
        else:
            return None

        try:
            ret = pg.fetchone(self.pg_conn, query)
        except pg.FeatureNotSupported:
            # Not implemented on Aurora (Issue #301)
            self.failed_queries.wal_receivers_query_failed = True
            logger.info(
                "The receiver information is not available on your platform. "
                "The feature is disabled. Please use the --no-walreceiver option."
            )
            return None

        return int(ret["wal_receivers"])

    def pg_get_replication_slots(self) -> Optional[int]:
        """
        Count the number of replication slots
        """
        if self.pg_num_version >= 140000:
            query = queries.get("get_replication_slots_post_140000")
        else:
            return None
        ret = pg.fetchone(self.pg_conn, query)
        return int(ret["replication_slots"])

    @property
    def dbname_filter(self) -> sql.Composable:
        if self.filters.dbname:
            return sql.Literal(self.filters.dbname)
        return sql.NULL

    def pg_get_server_information(
        self,
        prev_server_info: Optional[ServerInformation] = None,
        using_rds: bool = False,
        skip_db_size: bool = False,
        skip_tempfile: bool = False,
        skip_walreceiver: bool = False,
    ) -> ServerInformation:
        """
        Get the server information (session, workers, cache hit ratio etc..)
        """

        prev_total_size = 0
        if prev_server_info is not None:
            prev_total_size = prev_server_info.total_size

        if self.pg_num_version >= 110000:
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

        qs = sql.SQL(query).format(dbname_filter=self.dbname_filter)
        try:
            ret = pg.fetchone(
                self.pg_conn,
                qs,
                {
                    "dbname_filter": self.filters.dbname,
                    "skip_db_size": skip_db_size,
                    "prev_total_size": prev_total_size,
                    "using_rds": using_rds,
                },
            )
        except pg.InsufficientPrivilege:
            logger.info(
                "Privileges might be insufficient to connect to a database. "
                "Try to use a --filter, the --no-db-size option or a platform specific setting (eg. --rds)"
            )
            raise

        temporary_file_info: Optional[TempFileInfo] = None
        if not skip_tempfile:
            temporary_file_info = self.pg_get_temporary_file()
        wal_senders = self.pg_get_wal_senders()
        wal_receivers: Optional[int] = None
        if not skip_walreceiver:
            wal_receivers = self.pg_get_wal_receivers()
        replication_slots = self.pg_get_replication_slots()

        hr: Optional[Pct] = None
        tps, ips, ups, dps, rps = 0, 0, 0, 0, 0
        size_ev = 0.0
        if prev_server_info is not None:
            dt = float(ret["epoch"] - prev_server_info.epoch)
            try:
                # Note: All this could be negative just after a stat reset
                tps = int((ret["xact_count"] - prev_server_info.xact_count) / dt)
                size_ev = float(ret["total_size"] - prev_server_info.total_size) / dt
                ips = int((ret["insert"] - prev_server_info.insert) / dt)
                ups = int((ret["update"] - prev_server_info.update) / dt)
                dps = int((ret["delete"] - prev_server_info.delete) / dt)
                rps = int(
                    (ret["tuples_returned"] - prev_server_info.tuples_returned) / dt
                )
                deltaread = ret["blks_read"] - prev_server_info.blks_read
                deltahit = ret["blks_hit"] - prev_server_info.blks_hit
                if deltaread + deltahit != 0:
                    hr = Pct(100 * deltahit / (deltaread + deltahit))
            except ZeroDivisionError:
                pass

        return ServerInformation(
            size_evolution=size_ev,
            tps=tps,
            insert_per_second=ips,
            update_per_second=ups,
            delete_per_second=dps,
            tuples_returned_per_second=rps,
            cache_hit_ratio_last_snap=hr,
            temporary_file=temporary_file_info,
            wal_senders=wal_senders,
            wal_receivers=wal_receivers,
            replication_slots=replication_slots,
            **ret,
        )

    def pg_get_activities(self, duration_mode: int = 1) -> List[RunningProcess]:
        """
        Get activity from pg_stat_activity view.
        """
        if self.pg_num_version >= 130000:
            qs = queries.get("get_pg_activity_post_130000")
        elif self.pg_num_version >= 110000:
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
        query = sql.SQL(qs).format(
            dbname_filter=self.dbname_filter,
            duration_column=sql.Identifier(duration_column),
            min_duration=sql.Literal(self.min_duration),
        )

        return pg.fetchall(
            self.pg_conn,
            query,
            {
                "min_duration": self.min_duration,
                "dbname_filter": self.filters.dbname,
            },
            mkrow=partial(RunningProcess.from_bytes, self.server_encoding),
            text_as_bytes=True,
        )

    def pg_get_waiting(self, duration_mode: int = 1) -> List[WaitingProcess]:
        """
        Get waiting queries.
        """
        if self.pg_num_version >= 90200:
            qs = queries.get("get_waiting_post_090200")
        else:
            qs = queries.get("get_waiting_oldest")

        duration_column = self.get_duration_column(duration_mode)
        query = sql.SQL(qs).format(
            dbname_filter=self.dbname_filter,
            duration_column=sql.Identifier(duration_column),
            min_duration=sql.Literal(self.min_duration),
        )

        return pg.fetchall(
            self.pg_conn,
            query,
            {
                "min_duration": self.min_duration,
                "dbname_filter": self.filters.dbname,
            },
            mkrow=partial(WaitingProcess.from_bytes, self.server_encoding),
            text_as_bytes=True,
        )

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
        query = sql.SQL(qs).format(
            dbname_filter=self.dbname_filter,
            duration_column=sql.Identifier(duration_column),
            min_duration=sql.Literal(self.min_duration),
        )

        return pg.fetchall(
            self.pg_conn,
            query,
            {
                "min_duration": self.min_duration,
                "dbname_filter": self.filters.dbname,
            },
            mkrow=partial(BlockingProcess.from_bytes, self.server_encoding),
            text_as_bytes=True,
        )

    def pg_is_local(self) -> bool:
        """
        Is pg_activity connected locally?
        """
        query = queries.get("get_pga_inet_addresses")
        ret = pg.fetchone(self.pg_conn, query)
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
        except pg.OperationalError as err:
            errmsg = str(err).strip()
            if nb_try < 1 and (
                isinstance(err, pg.InvalidPassword)
                or errmsg.startswith("FATAL:  password authentication failed for user")
                or errmsg == "fe_sendauth: no password supplied"
            ):
                password = getpass.getpass()
            elif exit_on_failed:
                msg = str(err).replace("FATAL:", "")
                raise SystemExit("pg_activity: FATAL: %s" % clean_str(msg))
            else:
                raise Exception("Could not connect to PostgreSQL")
        except pg.ProgrammingError as err:
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
