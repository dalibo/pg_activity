import logging
import os
import socket
import sys
import time
from argparse import ArgumentParser
from io import StringIO
from typing import Optional

from blessed import Terminal

from . import __version__, data, types, ui
from .pg import OperationalError


def configure_logger(debug_file: Optional[str] = None) -> StringIO:
    logger = logging.getLogger("pgactivity")
    logger.setLevel(logging.DEBUG)

    # The steamhandler is used to print hints to the user at exit.
    # The INFO log level is reserved for this.
    memory_string = StringIO()
    c_handler = logging.StreamHandler(memory_string)
    c_handler.setLevel(logging.INFO)
    c_handler.name = "stream_handler"

    c_format = logging.Formatter("Hint - %(message)s")
    c_handler.setFormatter(c_format)

    logger.addHandler(c_handler)

    if debug_file is not None:
        f_handler = logging.FileHandler(debug_file)
        f_handler.setLevel(logging.DEBUG)

        f_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        f_handler.setFormatter(f_format)

        logger.addHandler(f_handler)

    return memory_string


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        usage="%(prog)s [options] [connection string]",
        description=(
            "htop like application for PostgreSQL server activity monitoring."
        ),
        epilog=(
            "The connection string can be in the form of a list of "
            "Key/Value parameters or an URI as described in the PostgreSQL documentation. "
            "The parsing is delegated to the libpq: different versions of the client library "
            "may support different formats or parameters (for example, connection URIs are "
            "only supported from libpq 9.2)."
        ),
        add_help=False,
    )

    group = parser.add_argument_group(
        "Options",
    )
    # --blocksize
    group.add_argument(
        "--blocksize",
        dest="blocksize",
        help="Filesystem blocksize (default: %(default)s).",
        metavar="BLOCKSIZE",
        type=int,
        default=4096,
    )
    # --rds
    group.add_argument(
        "--rds",
        dest="rds",
        action="store_true",
        help="Enable support for AWS RDS (implies --no-tempfiles and filters out the rdsadmin database from space calculation).",
        default=False,
    )
    # --output
    group.add_argument(
        "--output",
        dest="output",
        help="Store running queries as CSV.",
        metavar="FILEPATH",
        default=None,
    )
    # --no-db-size
    group.add_argument(
        "--no-db-size",
        dest="nodbsize",
        action="store_true",
        help="Skip total size of DB.",
        default=False,
    )
    # --no-tempfiles
    group.add_argument(
        "--no-tempfiles",
        dest="notempfiles",
        action="store_true",
        help="Skip tempfile count and size.",
        default=False,
    )
    # --no-walreceiver
    group.add_argument(
        "--no-walreceiver",
        dest="nowalreceiver",
        action="store_true",
        help="Skip walreceiver checks.",
        default=False,
    )
    # --wrap-query
    group.add_argument(
        "-w",
        "--wrap-query",
        dest="wrap_query",
        action="store_true",
        help="Wrap query column instead of truncating.",
        default=False,
    )
    # --duration-mode
    group.add_argument(
        "--duration-mode",
        dest="durationmode",
        help="Duration mode. Values: 1-QUERY(default), 2-TRANSACTION, 3-BACKEND.",
        metavar="DURATION_MODE",
        choices=["1", "2", "3"],
        default="1",
    )
    # --min-duration
    group.add_argument(
        "--min-duration",
        dest="minduration",
        help="Don't display queries with smaller than specified duration (in seconds).",
        metavar="SECONDS",
        type=float,
        default=0,
    )
    # --filter
    group.add_argument(
        "--filter",
        dest="filters",
        help=(
            "Filter activities with a (case insensitive) regular expression applied on selected fields. "
            "Known fields are: dbname."
        ),
        action="append",
        metavar="FIELD:REGEX",
        default=[],
    )
    # --debug-file
    group.add_argument(
        "--debug-file",
        dest="debug_file",
        metavar="DEBUG_FILE",
        help="Enable debug and write it to DEBUG_FILE.",
        default=None,
    )
    # --version
    group.add_argument(
        "--version",
        help="show program's version number and exit.",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    # --help
    group.add_argument(
        "--help",
        dest="help",
        action="store_true",
        help="Show this help message and exit.",
        default=False,
    )

    group = parser.add_argument_group(
        "Connection Options",
    )
    # Connection string
    group.add_argument(
        "connection_string",
        help=(
            "A valid connection string to the database, e.g.: "
            "'host=HOSTNAME port=PORT user=USER dbname=DBNAME'."
        ),
        nargs="?",
        metavar="connection string",
    )
    # -h / --host
    group.add_argument(
        "-h",
        "--host",
        dest="host",
        help="Database server host or socket directory.",
        metavar="HOSTNAME",
    )
    # -p / --port
    group.add_argument(
        "-p",
        "--port",
        dest="port",
        help="Database server port.",
        metavar="PORT",
    )
    # -U / --username
    group.add_argument(
        "-U",
        "--username",
        dest="username",
        help="Database user name.",
        metavar="USERNAME",
    )
    # -d / --dbname
    group.add_argument(
        "-d",
        "--dbname",
        dest="dbname",
        help="Database name to connect to.",
        metavar="DBNAME",
    )

    group = parser.add_argument_group(
        "Process table display options",
        "These options may be used hide some columns from the processes table.",
    )
    # --no-pid
    group.add_argument(
        "--no-pid",
        dest="nopid",
        action="store_true",
        help="Disable PID.",
        default=False,
    )
    # --no-database
    group.add_argument(
        "--no-database",
        dest="nodb",
        action="store_true",
        help="Disable DATABASE.",
        default=False,
    )
    # --no-user
    group.add_argument(
        "--no-user",
        dest="nouser",
        action="store_true",
        help="Disable USER.",
        default=False,
    )
    # --no-client
    group.add_argument(
        "--no-client",
        dest="noclient",
        action="store_true",
        help="Disable CLIENT.",
        default=False,
    )
    # --no-cpu
    group.add_argument(
        "--no-cpu",
        dest="nocpu",
        action="store_true",
        help="Disable CPU%%.",
        default=False,
    )
    # --no-mem
    group.add_argument(
        "--no-mem",
        dest="nomem",
        action="store_true",
        help="Disable MEM%%.",
        default=False,
    )
    # --no-read
    group.add_argument(
        "--no-read",
        dest="noread",
        action="store_true",
        help="Disable READ/s.",
        default=False,
    )
    # --no-write
    group.add_argument(
        "--no-write",
        dest="nowrite",
        action="store_true",
        help="Disable WRITE/s.",
        default=False,
    )
    # --no-time
    group.add_argument(
        "--no-time",
        dest="notime",
        action="store_true",
        help="Disable TIME+.",
        default=False,
    )
    # --no-wait
    group.add_argument(
        "--no-wait",
        dest="nowait",
        action="store_true",
        help="Disable W.",
        default=False,
    )
    # --no-app-name
    group.add_argument(
        "--no-app-name",
        dest="noappname",
        action="store_true",
        help="Disable App.",
        default=False,
    )

    group = parser.add_argument_group("Other display options")
    # --hide-queries-in-logs
    group.add_argument(
        "--hide-queries-in-logs",
        dest="hide_queries_in_logs",
        action="store_true",
        help="Disable log_min_duration_statements and log_min_duration_sample for pg_activity.",
        default=False,
    )
    # --no-inst-info
    group.add_argument(
        "--no-inst-info",
        dest="show_instance_info_in_header",
        action="store_false",
        help="Display instance information in header.",
        default=True,
    )
    # --no-sys-info
    group.add_argument(
        "--no-sys-info",
        dest="show_system_info_in_header",
        action="store_false",
        help="Display system information in header.",
        default=True,
    )
    # --no-proc-info
    group.add_argument(
        "--no-proc-info",
        dest="show_worker_info_in_header",
        action="store_false",
        help="Display workers process information in header.",
        default=True,
    )
    # --refresh
    group.add_argument(
        "--refresh",
        dest="refresh",
        help="Refresh rate. Values: %(choices)s (default: %(default)d).",
        metavar="REFRESH",
        choices=[0.5, 1, 2, 3, 4, 5],
        type=float,
        default=2,
    )

    return parser


def exit(msg: str) -> None:
    print("pg_activity: error: %s" % msg)
    print('Try "pg_activity --help" for more information.')
    sys.exit(1)


def main() -> None:
    if os.name != "posix":
        sys.exit("FATAL: Platform not supported.")

    parser = get_parser()
    args = parser.parse_args()
    memory_stream = configure_logger(args.debug_file)

    if args.help:
        parser.print_help()
        sys.exit(1)

    try:
        filters = types.Filters.from_options(args.filters)
    except ValueError as e:
        parser.error(str(e))
    if args.rds:
        args.notempfile = True

    dataobj = data.pg_connect(
        args,
        args.connection_string,
        min_duration=args.minduration,
        filters=filters,
    )
    hostname = socket.gethostname()
    conninfo = dataobj.pg_conn.info
    host = types.Host(
        hostname,
        conninfo.user,
        conninfo.host,
        int(conninfo.port),
        conninfo.dbname,
    )

    term = Terminal()
    while True:
        try:
            ui.main(term, dataobj, host, args)
        except OperationalError:
            while True:
                print(term.clear + term.home, end="")
                print("Connection to PostgreSQL lost, trying to reconnect...")
                try:
                    time.sleep(5)
                except KeyboardInterrupt:
                    sys.exit(1)
                newdataobj = dataobj.try_reconnect()
                if newdataobj is not None:
                    dataobj = newdataobj
                    break
        except KeyboardInterrupt:
            sys.exit(1)
        else:
            break
        finally:
            print(memory_stream.getvalue(), file=sys.stderr)
