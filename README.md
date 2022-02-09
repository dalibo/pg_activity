![pg_activity](https://github.com/dalibo/pg_activity/raw/master/docs/imgs/logo-horizontal.png)

Command line tool for PostgreSQL server activity monitoring.

[![Latest PyPI version](https://img.shields.io/pypi/v/pg_activity.svg)](https://pypi.python.org/pypi/pg_activity)
[![Lint](https://github.com/dalibo/pg_activity/actions/workflows/lint.yml/badge.svg)](https://github.com/dalibo/pg_activity/actions/workflows/lint.yml)
[![Tests](https://github.com/dalibo/pg_activity/actions/workflows/tests.yml/badge.svg)](https://github.com/dalibo/pg_activity/actions/workflows/tests.yml)

![pg_activity screenshot](https://raw.github.com/dalibo/pg_activity/master/docs/imgs/screenshot.png)

Installation from packages (recommended)
----------------------------------------

pg\_activity is available in many Linux distributions; the PostgreSQL Global
Development Group (PGDG) also provides packages for RPM-based
(https://yum.postgresql.org/) and Debian-based distributions
(https://wiki.postgresql.org/wiki/Apt):

    $ sudo yum install pg_activity

    $ sudo apt install pg-activity

Using distribution packages is the recommended way to install pg\_activity.

Installation from pip
---------------------

Alternatively, pg\_activity can be installed using pip on Python 3.7 or later
along with psycopg2 (version 2.8 or higher):

    $ python3 -m pip install pg_activity psycopg2-binary

In case your `$PATH` does not already contain it, the full path is:

    $ ~/.local/bin/pg_activity

Installation from the git repository
------------------------------------

This is only necessary to test development versions. First, clone the repository:

    $ git clone https://github.com/dalibo/pg_activity.git

Change the branch if necessary. Then create a dedicated environment,
install dependencies and then pg\_activity from the repo:

    $ cd pg_activity
    $ python3 -m venv .venv
    $ . .venv/bin/activate
    (.venv) $ pip install psycopg2-binary .
    (.venv) $ pg_activity

To quit this env and destroy it:

    $ deactivate
    $ rm -r .venv

Usage
-----

`pg_activity` works locally or remotely. In local execution context, to obtain
sufficient rights to display system informations, the system user running
`pg_activity` must be the same user running postgresql server (`postgres` by
default), or have more rights like `root`. Otherwise, `pg_activity` can fallback
to a degraded mode without displaying system informations. On the same way,
PostgreSQL user used to connect to the database must be super-user.
ex:

    sudo -u postgres pg_activity -U postgres

Options
-------

    pg_activity [options]

    Options:
        --version             Show program's version number and exit
        -U USERNAME, --username=USERNAME
                              Database user name (default: "postgres").
        -p PORT, --port=PORT  Database server port (default: "5432").
        -h HOSTNAME, --host=HOSTNAME
                              Database server host or socket directory (default:
                              "localhost").
        -d DBNAME, --dbname=DBNAME
                              Database name to connect to (default: "postgres").
        --blocksize=BLOCKSIZE Filesystem blocksize (default: 4096).
        --rds                 Enable support for AWS RDS.
        --output=FILEPATH     Store running queries as CSV.
        --help                Show this help message and exit.
        --no-db-size          Skip total size of DB.
        --duration-mode=DURATION_MODE
                              Duration mode. Values: 1-QUERY(default),
                              2-TRANSACTION, 3-BACKEND
        --min-duration        Don't display queries with smaller than specified
                              duration (in seconds).
        --filter=FIELD:REGEX  Filter activities with a (case insensitive) regular
                              expression applied on selected fields. Known fields
                              are: dbname.
        --verbose-mode=VERBOSE_MODE
                              Queries display mode. Values: 1-TRUNCATED,
                              2-FULL(default), 3-INDENTED


    Display options, you can exclude some columns by using them :
        --no-database         Disable DATABASE.
        --no-user             Disable USER.
        --no-client           Disable CLIENT.
        --no-cpu              Disable CPU%.
        --no-mem              Disable MEM%.
        --no-read             Disable READ/s.
        --no-write            Disable WRITE/s.
        --no-time             Disable TIME+.
        --no-wait             Disable W.
        --no-app-name         Disable App.


Notes
-----

Length of SQL query text that `pg_activity` reports relies on PostgreSQL
parameter `track_activity_query_size`. Default value is `1024` (expressed in
bytes). If your SQL query text look truncated, you should increase
`track_activity_query_size`.


Interactives commands
---------------------

| Key       | Action                                                           |
|-----------|------------------------------------------------------------------|
| `r`       | Sort by READ/s, descending                                       |
| `w`       | Sort by WRITE/s, descending                                      |
| `c`       | Sort by CPU%, descending                                         |
| `m`       | Sort by MEM%, descending                                         |
| `t`       | Sort by TIME+, descending                                        |
| `T`       | Change duration mode: query, transaction, backend                |
| `Space`   | Pause on/off                                                     |
| `v`       | Change queries display mode: full, indented, truncated           |
| `UP/DOWN` | Scroll processes list                                            |
| `k/j`     | Scroll processes list                                            |
| `q`       | Quit                                                             |
| `+`       | Increase refresh time. Maximum value : 5s                        |
| `-`       | Decrease refresh time. Minimum Value : 0.5s                      |
| `F1/1`    | Running queries list                                             |
| `F2/2`    | Waiting queries list                                             |
| `F3/3`    | Blocking queries list                                            |
| `h`       | Help page                                                        |
| `R`       | Refresh                                                          |
| `D`       | Refresh Database Size (including when --no-dbzise option applied)|

Navigation mode
---------------

| Key        | Action                                        |
|------------|-----------------------------------------------|
| `UP`/`k`   | Move up the cursor                            |
| `DOWN`/`j` | Move down the cursor                          |
| `K`        | Terminate the current backend/tagged backends |
| `C`        | Cancel the current backend/tagged backends    |
| `Space`    | Tag or untag the process                      |
| `q`        | Quit                                          |
| `Other`    | Back to activity                              |

FAQ
---

**I can't see my queries only TPS is shown**

`pg_activity` scans the view `pg_stat_activity` with a user defined refresh
time comprised between O.5 and 5 seconds. It can be modified in the interface
with the `+` and `-` keys. Any query executed between two scans won't be
displayed.


What is more, `pg_activity` uses different queries to get :

*    settings from `pg_settings`
*    version info using `version()`
*    queries and number of connections from `pg_stat_activity`
*    locks from `pg_locks`
*    tps from `pg_database` using `pg_stat_get_db_xact_commit()` and
     `pg_stat_get_db_xact_rollback()`
*    and more ( eg : `pg_cancel_backend()` and `pg_terminate_backend()` )

Thoses queries cannot be seen in the query tab because all queries issued from
the `pg_activity` backend are considered as noise and are not displayed . On
the other hand, the transactions used to get the info for `pg_activity`'s
reporting are still accounted for by postgres in `pg_stat_get_db_xact_commit()`
and `pg_stat_get_db_xact_commit()`. Therefore `pg_activity` will display a non
zero TPS even with no activity on the database, and/or no activity displayed on
screen.

**How can I specify a password for authentication ?**

pg_activity uses libpq to access to PostgreSQL therefore all the traditional
methods are available.

You can pass the password for the database connection in a password file.
Information can also be given via PostgreSQL's environment variables
(PGPASSFILE or PGPASSWORD) or via the connection string parameters.

The password file is preferred since it's more secure (security is deferred to
the OS). Please avoid password in connection strings at all cost.

