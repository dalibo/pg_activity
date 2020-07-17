import getpass
import optparse
import re
import sys
from typing import Any, Optional

import psycopg2
from psycopg2 import errorcodes


def clean_str(string: str) -> str:
    r"""
    Strip and replace some special characters.

    >>> clean_str("\n")
    ''
    >>> clean_str("\n a a  b   b    c \n\t\n c\v\n")
    'a a b b c c'
    """
    msg = str(string)
    msg = msg.replace("\n", " ")
    msg = re.sub(r"\s+", r" ", msg)
    msg = re.sub(r"^\s", r"", msg)
    msg = re.sub(r"\s$", r"", msg)
    return msg


def pg_connect(
    data: Any,
    options: optparse.Values,
    password: Optional[str] = None,
    service: Optional[str] = None,
    exit_on_failed: bool = True,
) -> Optional[str]:
    """Try to connect to postgres using 'data' instance, return the password
    to be used in case of reconnection.
    """
    for nb_try in range(2):
        try:
            data.pg_connect(
                host=options.host,
                port=options.port,
                user=options.username,
                password=password,
                database=options.dbname,
                rds_mode=options.rds,
                service=service,
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
                sys.exit("pg_activity: FATAL: %s" % clean_str(msg))
            else:
                raise Exception("Could not connect to PostgreSQL")
        else:
            break
    return password
