import os
import socket
import sys
import time
from optparse import OptionParser, OptionGroup
from typing import NoReturn

from blessed import Terminal
from psycopg2.errors import OperationalError

from . import __version__, data, types, ui


# Customized OptionParser
class ModifiedOptionParser(OptionParser):
    """
    ModifiedOptionParser
    """

    def error(self, msg: str) -> NoReturn:
        raise OptionParsingError(msg)


class OptionParsingError(RuntimeError):
    """
    OptionParsingError
    """

    def __init__(self, msg: str) -> None:
        self.msg = msg


def get_parser() -> ModifiedOptionParser:
    parser = ModifiedOptionParser(
        add_help_option=False,
        version="%prog " + __version__,
        usage="%prog [options] [connection string]",
        epilog=(
            "The connection string can be in the form of a list of "
            "Key/Value parameters or an URI as described in the PostgreSQL documentation. "
            "The parsing is delegated to the libpq: different versions of the client library "
            "may support different formats or parameters (for example, connection URIs are "
            "only supported from libpq 9.2)"
        ),
        description=(
            "htop like application for PostgreSQL " "server activity monitoring."
        ),
    )
    # -U / --username
    parser.add_option(
        "-U",
        "--username",
        dest="username",
        help="Database user name",
        metavar="USERNAME",
    )
    # -p / --port
    parser.add_option(
        "-p",
        "--port",
        dest="port",
        help="Database server port",
        metavar="PORT",
    )
    # -h / --host
    parser.add_option(
        "-h",
        "--host",
        dest="host",
        help="Database server host or socket directory",
        metavar="HOSTNAME",
    )
    # -d / --dbname
    parser.add_option(
        "-d",
        "--dbname",
        dest="dbname",
        help="Database name to connect to",
        metavar="DBNAME",
    )
    # --blocksize
    parser.add_option(
        "--blocksize",
        dest="blocksize",
        help="Filesystem blocksize (default: %default)",
        metavar="BLOCKSIZE",
        default=4096,
    )
    # --rds
    parser.add_option(
        "--rds",
        dest="rds",
        action="store_true",
        help="Enable support for AWS RDS",
        default=False,
    )
    # --output
    parser.add_option(
        "--output",
        dest="output",
        help="Store running queries as CSV",
        metavar="FILEPATH",
        default=None,
    )
    # --help
    parser.add_option(
        "--help",
        dest="help",
        action="store_true",
        help="Show this help message and exit",
        default=False,
    )
    # --no-db-size
    parser.add_option(
        "--no-db-size",
        dest="nodbsize",
        action="store_true",
        help="Skip total size of DB",
        default=False,
    )
    # --verbose-mode
    parser.add_option(
        "--verbose-mode",
        dest="verbosemode",
        help="Queries display mode. Values: 1-TRUNCATED, 2-FULL(default), 3-INDENTED",
        metavar="VERBOSE_MODE",
        choices=["1", "2", "3"],
        default="2",
    )
    # --duration-mode
    parser.add_option(
        "--duration-mode",
        dest="durationmode",
        help="Duration mode. Values: 1-QUERY(default), 2-TRANSACTION, 3-BACKEND",
        metavar="DURATION_MODE",
        choices=["1", "2", "3"],
        default="1",
    )
    # --min-duration
    parser.add_option(
        "--min-duration",
        dest="minduration",
        help="Don't display queries with smaller than specified duration (in seconds)",
        metavar="SECONDS",
        type=float,
        default=0,
    )

    group = OptionGroup(
        parser, "Display Options, you can exclude some columns by using them "
    )
    # --no-pid
    group.add_option(
        "--no-pid",
        dest="nopid",
        action="store_true",
        help="Disable PID.",
        default=False,
    )
    # --no-database
    group.add_option(
        "--no-database",
        dest="nodb",
        action="store_true",
        help="Disable DATABASE",
        default=False,
    )
    # --no-user
    group.add_option(
        "--no-user",
        dest="nouser",
        action="store_true",
        help="Disable USER",
        default=False,
    )
    # --no-client
    group.add_option(
        "--no-client",
        dest="noclient",
        action="store_true",
        help="Disable CLIENT",
        default=False,
    )
    # --no-cpu
    group.add_option(
        "--no-cpu",
        dest="nocpu",
        action="store_true",
        help="Disable CPU%",
        default=False,
    )
    # --no-mem
    group.add_option(
        "--no-mem",
        dest="nomem",
        action="store_true",
        help="Disable MEM%",
        default=False,
    )
    # --no-read
    group.add_option(
        "--no-read",
        dest="noread",
        action="store_true",
        help="Disable READ/s",
        default=False,
    )
    # --no-write
    group.add_option(
        "--no-write",
        dest="nowrite",
        action="store_true",
        help="Disable WRITE/s",
        default=False,
    )
    # --no-time
    group.add_option(
        "--no-time",
        dest="notime",
        action="store_true",
        help="Disable TIME+",
        default=False,
    )
    # --no-wait
    group.add_option(
        "--no-wait", dest="nowait", action="store_true", help="Disable W", default=False
    )
    # --no-app-name
    group.add_option(
        "--no-app-name",
        dest="noappname",
        action="store_true",
        help="Disable App",
        default=False,
    )
    # --hide-queries-in-logs
    group.add_option(
        "--hide-queries-in-logs",
        dest="hide_queries_in_logs",
        action="store_true",
        help="Disable log_min_duration_statements and log_min_duration_sample for pg_activity",
        default=False,
    )

    parser.add_option_group(group)

    return parser


def exit(msg: str) -> None:
    print("pg_activity: error: %s" % msg)
    print('Try "pg_activity --help" for more information.')
    sys.exit(1)


def main() -> None:
    if os.name != "posix":
        sys.exit("FATAL: Platform not supported.")
    try:
        parser = get_parser()
        (options, args) = parser.parse_args()
        if len(args) == 1:
            dsn = args[0]
        elif len(args) > 1:
            raise OptionParsingError("at most one argument is expected")
        else:
            dsn = ""

    except OptionParsingError as err:
        exit(err.msg)
    if options.help:
        print(parser.format_help().strip())
        sys.exit(1)

    dataobj = data.pg_connect(
        options,
        dsn,
        min_duration=options.minduration,
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
            ui.main(term, dataobj, host, options, dsn)
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
                    print(term.clear + term.home, end="")
                    break
        else:
            print(term.clear + term.home, end="")
            break
