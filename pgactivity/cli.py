from __future__ import annotations

import argparse
import logging
import os
import socket
import sys
import time
from io import StringIO
from typing import Any

from blessed import Terminal

from . import __version__, data, types, ui
from .config import Configuration, ConfigurationError
from .pg import OperationalError


def configure_logger(debug_file: str | None = None) -> StringIO:
    logger = logging.getLogger("pgactivity")
    logger.setLevel(logging.DEBUG)

    # The steamhandler is used to print all messages at exit.
    memory_string = StringIO()
    c_handler = logging.StreamHandler(memory_string)
    c_handler.setLevel(logging.INFO)
    c_handler.name = "stream_handler"

    c_format = logging.Formatter("%(levelname)s - %(message)s")
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


def flag(p: Any, spec: str, *, dest: str, feature: str) -> None:
    assert not spec.startswith("--no-") and spec.startswith("--"), spec
    p.add_argument(
        spec,
        dest=dest,
        help=f"Enable/disable {feature}.",
        action=argparse.BooleanOptionalAction,
        default=None,
    )


def get_parser(prog: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
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
        "Configuration",
    )
    group.add_argument(
        "-P",
        "--profile",
        help=(
            "Configuration profile matching a PROFILE.conf file in "
            "${XDG_CONFIG_HOME:~/.config}/pg_activity/ or /etc/pg_activity/, "
            "or a built-in profile."
        ),
    )

    group = parser.add_argument_group(
        "Options",
    )
    group.add_argument(
        "--blocksize",
        dest="blocksize",
        help="Filesystem blocksize (default: %(default)s).",
        metavar="BLOCKSIZE",
        type=int,
        default=4096,
    )
    group.add_argument(
        "--rds",
        dest="rds",
        action="store_true",
        help="Enable support for AWS RDS (implies --no-tempfiles and filters out the rdsadmin database from space calculation).",
        default=False,
    )
    group.add_argument(
        "--output",
        dest="output",
        help="Store running queries as CSV.",
        metavar="FILEPATH",
        default=None,
    )
    flag(group, "--db-size", dest="dbsize", feature="total size of DB")
    flag(group, "--tempfiles", dest="tempfiles", feature="tempfile count and size")
    flag(group, "--walreceiver", dest="walreceiver", feature="walreceiver checks")
    group.add_argument(
        "-w",
        "--wrap-query",
        dest="wrap_query",
        action="store_true",
        help="Wrap query column instead of truncating.",
        default=False,
    )
    group.add_argument(
        "--duration-mode",
        dest="durationmode",
        help="Duration mode. Values: 1-QUERY(default), 2-TRANSACTION, 3-BACKEND.",
        metavar="DURATION_MODE",
        choices=["1", "2", "3"],
        default="1",
    )
    group.add_argument(
        "--min-duration",
        dest="minduration",
        help="Don't display queries with smaller than specified duration (in seconds).",
        metavar="SECONDS",
        type=float,
        default=0,
    )
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
    group.add_argument(
        "--debug-file",
        dest="debug_file",
        metavar="DEBUG_FILE",
        help="Enable debug and write it to DEBUG_FILE.",
        default=None,
    )
    group.add_argument(
        "--version",
        help="show program's version number and exit.",
        action="version",
        version=f"%(prog)s {__version__}",
    )
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
        default="",
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
    flag(group, "--pid", dest="pid", feature="PID")
    flag(group, "--xmin", dest="xmin", feature="XMIN")
    flag(group, "--database", dest="database", feature="DATABASE")
    flag(group, "--user", dest="user", feature="USER")
    flag(group, "--client", dest="client", feature="CLIENT")
    flag(group, "--cpu", dest="cpu", feature="CPU%%")
    flag(group, "--mem", dest="mem", feature="MEM%%")
    flag(group, "--read", dest="read", feature="READ/s")
    flag(group, "--write", dest="write", feature="WRITE/s")
    flag(group, "--time", dest="time", feature="TIME+")
    flag(group, "--wait", dest="wait", feature="W")
    flag(group, "--app-name", dest="appname", feature="APP")

    group = parser.add_argument_group("Header display options")
    group.add_argument(
        "--no-inst-info",
        dest="header_show_instance",
        action="store_false",
        help="Hide instance information.",
        default=None,
    )
    group.add_argument(
        "--no-sys-info",
        dest="header_show_system",
        action="store_false",
        help="Hide system information.",
        default=None,
    )
    group.add_argument(
        "--no-proc-info",
        dest="header_show_workers",
        action="store_false",
        help="Hide workers process information.",
        default=None,
    )

    group = parser.add_argument_group("Other display options")
    group.add_argument(
        "--hide-queries-in-logs",
        dest="hide_queries_in_logs",
        action="store_true",
        help="Disable log_min_duration_statements and log_min_duration_sample for pg_activity.",
        default=False,
    )
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

    try:
        cfg = Configuration.lookup(args.profile)
    except (ConfigurationError, FileNotFoundError) as e:
        parser.error(str(e))

    try:
        dataobj = data.pg_connect(args, min_duration=args.minduration, filters=filters)
    except OperationalError as e:
        parser.exit(status=1, message=f"could not connect to PostgreSQL: {e}")
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
            ui.main(term, cfg, dataobj, host, args)
        except ConfigurationError as e:
            parser.exit(1, f"error: {e}")
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
            sys.exit(0)
        else:
            break
        finally:
            print(memory_stream.getvalue(), file=sys.stderr)
