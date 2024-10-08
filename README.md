![pg_activity](https://github.com/dalibo/pg_activity/raw/master/docs/imgs/logo-horizontal.png)

Command line tool for PostgreSQL server activity monitoring.

[![Latest PyPI version](https://img.shields.io/pypi/v/pg_activity.svg)](https://pypi.python.org/pypi/pg_activity)
[![Lint](https://github.com/dalibo/pg_activity/actions/workflows/lint.yml/badge.svg)](https://github.com/dalibo/pg_activity/actions/workflows/lint.yml)
[![Tests](https://github.com/dalibo/pg_activity/actions/workflows/tests.yml/badge.svg)](https://github.com/dalibo/pg_activity/actions/workflows/tests.yml)

![pg_activity screenshot](https://raw.github.com/dalibo/pg_activity/master/docs/imgs/screenshot.png)

# Installation

## From distribution packages

The simplest way to install pg\_activity is through the package manager of your
Linux distribution, if it ships with a package. E.g., on Debian-based
distributions (e.g. Debian, Ubuntu, Mint...):

    $ sudo apt install pg-activity

(on Debian bullseye, the current stable version, a backport is available: `apt
install pg-activity/bullseye-backports`).

The PostgreSQL Global Development Group (PGDG) also provides packages for
RPM-based (https://yum.postgresql.org/) and Debian-based distributions
(https://wiki.postgresql.org/wiki/Apt).

**Note:** distribution packages may not be up to date with the latest
pg\_activity releases. Before submitting a bug report here:
-   check the package version, compare that to our latest release and then
    review the [change log][changelog] to see if the bug has been fixed;
-   if the issue is about packaging, e.g. missing dependencies, reach out
    the package maintainer (or PGDG) first.

## From PyPI

pg\_activity can be installed using pip on Python 3.8 or later along with
psycopg:

    $ python3 -m pip install "pg_activity[psycopg]"

Alternatively, [pipx](https://pypi.org/project/pipx/) can be used to install
and run pg\_activity in an isolated environment:

    $ pipx install "pg_activity[psycopg]"

In case your `$PATH` does not already contain it, the full path is:

    $ ~/.local/bin/pg_activity

## From source, using git

This is only necessary to test development versions. First, clone the repository:

    $ git clone https://github.com/dalibo/pg_activity.git

Change the branch if necessary. Then create a dedicated environment,
and install pg\_activity with the psycopg database driver:

    $ cd pg_activity
    $ python3 -m venv .venv
    $ . .venv/bin/activate
    (.venv) $ pip install ".[psycopg]"
    (.venv) $ pg_activity

To quit this env and destroy it:

    $ deactivate
    $ rm -r .venv

# Usage

`pg_activity` works locally or remotely. In local execution context, to obtain
sufficient rights to display system information, the system user running
`pg_activity` must be the same user running postgresql server (`postgres` by
default), or have more rights like `root`. The PostgreSQL user used to connect
to the database must be super-user in order to get as much data as possible.
Otherwise, `pg_activity` can fall back to a degraded mode where some data like
system information or temporary file data are not displayed.

ex:

    sudo -u postgres pg_activity -U postgres

## Options

    pg_activity [options] [connection string]

    Configuration:
      -P, --profile PROFILE
                            Configuration profile matching a PROFILE.conf file in
                            ${XDG_CONFIG_HOME:~/.config}/pg_activity/ or
                            /etc/pg_activity/, or a built-in profile.

    Options:
      --blocksize BLOCKSIZE
                            Filesystem blocksize (default: 4096).
      --rds                 Enable support for AWS RDS (implies --no-tempfiles and
                            filters out the rdsadmin database from space
                            calculation).
      --output FILEPATH     Store running queries as CSV.
      --db-size, --no-db-size
                            Enable/disable total size of DB.
      --tempfiles, --no-tempfiles
                            Enable/disable tempfile count and size.
      --walreceiver, --no-walreceiver
                            Enable/disable walreceiver checks.
      -w, --wrap-query      Wrap query column instead of truncating.
      --duration-mode DURATION_MODE
                            Duration mode. Values: 1-QUERY(default),
                            2-TRANSACTION, 3-BACKEND.
      --min-duration SECONDS
                            Don't display queries with smaller than specified
                            duration (in seconds).
      --filter FIELD:REGEX  Filter activities with a (case insensitive) regular
                            expression applied on selected fields. Known fields
                            are: dbname.
      --debug-file DEBUG_FILE
                            Enable debug and write it to DEBUG_FILE.
      --version             show program's version number and exit.
      --help                Show this help message and exit.

    Connection Options:
      connection string     A valid connection string to the database, e.g.:
                            'host=HOSTNAME port=PORT user=USER dbname=DBNAME'.
      -h, --host HOSTNAME   Database server host or socket directory.
      -p, --port PORT       Database server port.
      -U, --username USERNAME
                            Database user name.
      -d, --dbname DBNAME   Database name to connect to.

    Process table display options:
      These options may be used hide some columns from the processes table.

      --pid, --no-pid       Enable/disable PID.
      --database, --no-database
                            Enable/disable DATABASE.
      --user, --no-user     Enable/disable USER.
      --client, --no-client
                            Enable/disable CLIENT.
      --cpu, --no-cpu       Enable/disable CPU%.
      --mem, --no-mem       Enable/disable MEM%.
      --read, --no-read     Enable/disable READ/s.
      --write, --no-write   Enable/disable WRITE/s.
      --time, --no-time     Enable/disable TIME+.
      --wait, --no-wait     Enable/disable W.
      --app-name, --no-app-name
                            Enable/disable APP.

    Header display options:
      --no-inst-info        Display instance information.
      --no-sys-info         Display system information.
      --no-proc-info        Display workers process information.

    Other display options:
      --hide-queries-in-logs
                            Disable log_min_duration_statements and
                            log_min_duration_sample for pg_activity.
      --refresh REFRESH     Refresh rate. Values: 0.5, 1, 2, 3, 4, 5 (default: 2).

## Configuration

`pg_activity` may be configured through a configuration file, in [INI format][],
read from `${XDG_CONFIG_HOME:~/.config}/pg_activity.conf` or
`/etc/pg_activity.conf` in that order. Command-line options may override
configuration file settings.
This is used to control how columns in the processes table are rendered or which
items of the header should be displayed, e.g.:
```ini
[header]
show_instance = yes
show_system = yes
show_workers = no

[client]
hidden = yes

[database]
width = 9
```

Alternatively, the user might define *configuration profiles* in the form of
files located at `${XDG_CONFIG_HOME:~/.config}/pg_activity/<my-profile>.conf` or
`/etc/pg_activity/<my-profile>.conf`; these can then be used through the
`--profile <my-profile>` command-line option. The format of these files is the
same as the main configuration file.

`pg_activity` ships with a few built-in profiles:

- `narrow`, providing a narrow user interface with most non-essential
  columns in the process table hidden,
- `wide`, providing a wide user interface (the inverse of `narrow`), and,
- `minimal`, providing an even more minimal user interface with header
  information hidden

Columns of the process table in pg\_activity user interface can be assigned a
custom color in the configuration file, e.g.:
```ini
[client]
color = magenta

[relation]
color = red
```

The `color` option illustrated above defines the color used to render the cell
independently of its value, i.e. the "normal" color. Some columns may be
colorized differently depending on the value of their cells; for example, the
`time` column can handle tree colors depending on whether the time value is
*high*, *medium* or *low*. The color of such columns cannot be currently
customized and attempting to do so will result in pg\_activity to exit early
with an error message.

[INI format]: https://docs.python.org/3/library/configparser.html#supported-ini-file-structure

## Notes

Length of SQL query text that `pg_activity` reports relies on PostgreSQL
parameter `track_activity_query_size`. Default value is `1024` (expressed in
bytes). If your SQL query text look truncated, you should increase
`track_activity_query_size`.


## Interactives commands

| Key       | Action                                                           |
|-----------|------------------------------------------------------------------|
| `r`       | Sort by READ/s, descending                                       |
| `w`       | Sort by WRITE/s, descending                                      |
| `c`       | Sort by CPU%, descending                                         |
| `m`       | Sort by MEM%, descending                                         |
| `t`       | Sort by TIME+, descending                                        |
| `y`       | Copy focused query to clipboard                                  |
| `T`       | Change duration mode: query, transaction, backend                |
| `Space`   | Pause on/off                                                     |
| `v`       | Change queries display mode: full, indented, truncated           |
| `UP/DOWN` | Scroll processes list                                            |
| `k/j`     | Scroll processes list                                            |
| `q`       | Quit                                                             |
| `+`       | Increase refresh time. Maximum value: 5s                         |
| `-`       | Decrease refresh time. Minimum Value: 0.5s                       |
| `F1/1`    | Running queries list                                             |
| `F2/2`    | Waiting queries list                                             |
| `F3/3`    | Blocking queries list                                            |
| `h`       | Help page                                                        |
| `R`       | Refresh                                                          |
| `D`       | Refresh Database Size (including when --no-dbzise option applied)|
| `s`       | Display system information in header                             |
| `i`       | Display general instance information in header                   |
| `o`       | Display worker information in header                             |

## Navigation mode

| Key        | Action                                        |
|------------|-----------------------------------------------|
| `UP`/`k`   | Move up the cursor                            |
| `DOWN`/`j` | Move down the cursor                          |
| `K`        | Terminate the current backend/tagged backends |
| `C`        | Cancel the current backend/tagged backends    |
| `Space`    | Tag or untag the process                      |
| `q`        | Quit                                          |
| `Other`    | Back to activity                              |

## FAQ

**I can't see my queries only TPS is shown**

`pg_activity` scans the view `pg_stat_activity` with a user defined refresh
time comprised between 0.5 and 5 seconds. It can be modified in the interface
with the `+` and `-` keys. Any query executed between two scans won't be
displayed.


What is more, `pg_activity` uses different queries to get:

*    settings from `pg_settings`
*    version info using `version()`
*    queries and number of connections from `pg_stat_activity`
*    locks from `pg_locks`
*    tps from `pg_database` using `pg_stat_get_db_xact_commit()` and
     `pg_stat_get_db_xact_rollback()`
*    and more (e.g.: `pg_cancel_backend()` and `pg_terminate_backend()`)

Those queries cannot be seen in the query tab because all queries issued from
the `pg_activity` backend are considered as noise and are not displayed . On
the other hand, the transactions used to get the info for `pg_activity`'s
reporting are still accounted for by postgres in `pg_stat_get_db_xact_commit()`
and `pg_stat_get_db_xact_commit()`. Therefore `pg_activity` will display a non
zero TPS even with no activity on the database, and/or no activity displayed on
screen.

**How can I specify a password for authentication?**

pg_activity uses libpq to access to PostgreSQL therefore all the traditional
methods are available.

You can pass the password for the database connection in a password file.
Information can also be given via PostgreSQL's environment variables
(PGPASSFILE or PGPASSWORD) or via the connection string parameters.

The password file is preferred since it's more secure (security is deferred to
the OS). Please avoid password in connection strings at all cost.

**How to copy/paste the query of focused process?**

The `y` shortcut will copy the query of focused process to system clipboard
using OSC 52 escape sequence. This requires the terminal emulator to support
this escape sequence and set the clipboard accordingly. If so, the copy even
works across remote connections (SSH). In general, terminal emulators supporting
this would use `CTRL+SHIFT+V` to paste from this clipboard.

# Hacking

In order to work on pg\_activity source code, in particular to run the tests
suite, a temporary PostgreSQL database cluster will be created; accordingly,
PostgreSQL server binaries (e.g. `initdb`, `pg_ctl`) need to be available. For
instance, on a Debian system, this means simply having the `postgresql` package
installed.

To set up a development environment, get the source repository:

    $ git clone https://github.com/dalibo/pg_activity
    $ cd pg_activity

and then create a [virtual environment][venv], activate it and install the
project along with development dependencies:

    $ python3 -m venv .venv
    $ .venv/bin/activate
    (.venv) $ pip install -e ".[dev]"

The source code is formatted with [black][] and [isort][] and typed checked with
[mypy][] (all those are included in the development environment). Make sure to
respect this, e.g. by configuring your editor, before committing changes.
Alternatively, you can install [pre-commit][] hooks so that this will be checked
automatically:

    (.venv) $ pre-commit install

[venv]: https://docs.python.org/3/library/venv.html
[black]: https://black.readthedocs.io/
[isort]: https://pycqa.github.io/isort/
[mypy]: https://mypy.readthedocs.io/
[pre-commit]: https://pre-commit.com/

To run the tests suite, simply invoke:

    (.venv) $ pytest
    ================================ test session starts =================================
    platform linux -- Python 3.11.2, pytest-7.3.1, pluggy-1.0.0
    psycopg: 3.1.8
    configfile: pytest.ini
    plugins: cov-4.0.0, accept-0.1.9, postgresql-4.1.1
    collected 70 items

    pgactivity/activities.py ..                                                    [  2%]
    pgactivity/config.py ..                                                        [  5%]
    pgactivity/data.py ..                                                          [  8%]
    pgactivity/handlers.py .....                                                   [ 15%]
    pgactivity/keys.py .                                                           [ 17%]
    pgactivity/types.py ..............                                             [ 37%]
    pgactivity/utils.py .........                                                  [ 50%]
    pgactivity/views.py .....                                                      [ 57%]
    tests/test_activities.py ...                                                   [ 61%]
    tests/test_config.py ..                                                        [ 64%]
    tests/test_data.py ................                                            [ 87%]
    tests/test_scroll.txt .                                                        [ 88%]
    tests/test_types.py .                                                          [ 90%]
    tests/test_ui.txt .                                                            [ 91%]
    tests/test_views.py ....                                                       [ 97%]
    tests/test_views.txt .                                                         [ 98%]
    tests/test_widgets.txt .                                                       [100%]

    ================================ 70 passed in 11.89s =================================

# Change log

See [CHANGELOG.md][changelog].

[changelog]: https://github.com/dalibo/pg_activity/blob/master/CHANGELOG.md
