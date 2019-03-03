[![Latest PyPI version](https://img.shields.io/pypi/v/pg_activity.svg)](https://pypi.python.org/pypi/pg_activity)

pg_activity
===========

Command line tool for PostgreSQL server activity monitoring.

Dependencies
------------

  - `python` &ge; **2.6**
  - `psycopg2` &ge; **2.2.1**
  - `psutil` &ge;  **0.5.1**

Installation from sources:
`setuptools` &ge; **0.6.14**

Installation
------------

    sudo python setup.py install

### Installation with man page

    sudo python setup.py install --with-man


Usage
-----

`pg_activity` works localy or remotely. In local execution context, to obtain sufficient rights to display system informations, the system user running `pg_activity` must be the same user running postgresql server (`postgres` by default), or have more rights like `root`. Otherwise, `pg_activity` can fallback to a degraded mode without displaying system informations. On the same way, PostgreSQL user used to connect to the database must be super-user.
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
        -C, --no-color        Disable color usage.
        --blocksize=BLOCKSIZE Filesystem blocksize (default: 4096).
        --rds                 Enable support for AWS RDS.
        --output=FILEPATH     Store running queries as CSV.
        --help                Show this help message and exit.
        --debug               Enable debug mode for traceback tracking.
        --no-db-size          Skip total size of DB.
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

Length of SQL query text that pg_activity reports relies on PostgreSQL parameter `track_activity_query_size`. Default value is `1024` (expressed in bytes). If your SQL query text look truncated, you should increase `track_activity_query_size`.


Interactives commands
---------------------

| Key       | Action                                                 |
|-----------|--------------------------------------------------------|
| `C`       | Activate/deactivate colors                             |
| `r`       | Sort by READ/s, descending                             |
| `w`       | Sort by WRITE/s, descending                            |
| `c`       | Sort by CPU%, descending                               |
| `m`       | Sort by MEM%, descending                               |
| `t`       | Sort by TIME+, descending                              |
| `Space`   | Pause on/off                                           |
| `v`       | Change queries display mode: full, truncated, indented |
| `UP/DOWN` | Scroll processes list                                  |
| `q`       | Quit                                                   |
| `+`       | Increase refresh time. Maximum value : 3s              |
| `-`       | Decrease refresh time. Minimum Value : 1s              |
| `F1/1`    | Running queries list                                   |
| `F2/2`    | Waiting queries list                                   |
| `F3/3`    | Blocking queries list                                  |
| `h`       | Help page                                              |
| `R`       | Refresh                                                |

Navigation mode
---------------

| Key     | Action                                        |
|---------|-----------------------------------------------|
| `UP`    | Move up the cursor                            |
| `DOWN`  | Move down the cursor                          |
| `k`     | Terminate the current backend/tagged backends |
| `Space` | Tag or untag the process                      |
| `q`     | Quit                                          |
| `Other` | Back to activity                              |
			
Screenshot
----------

![pg_activity screenshot](https://raw.github.com/julmon/pg_activity/master/docs/imgs/screenshot.png)
