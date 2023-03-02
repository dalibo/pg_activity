# Change log

## pg\_activity 3.1.0 - 2023-03-01

### Added

* Add support for Psycopg 3 database driver, as an alternative to psycopg2.
  Packagers and users installing from `pip` are encouraged to install the
  `psycopg` dependency instead of psycopg2.
* Add `psycopg` and `psycopg2` setuptools extras to ease complete installation
  from pip.
* Prepare statements for execution when using the `psycopg` database driver for
  better performance.

### Fixed

* Rework decoding of the `query` column to (hopefully) make it more robust
  (see #149 for the original report, #302 for a new problem raised while fixing
  the previous one and #332 for the latest update).
* Fix a few typos in the man page.

### Misc.

* Add a change log file and update the release how-to accordingly.
* Use [codespell](https://github.com/codespell-project/codespell) to check
  misspellings.
* Add Project-URLs core metadata for Python packaging.
* Install the project in *develop* mode in Tox test environment.
* Require blessed >= 1.15.0, as earlier versions are not compatible with Python
  3.7.

## pg\_activity 3.0.2  - 2023-01-17

### Fixed

* Fix a regression where pg\_activity would crash if the pidfile could not be
  read.
* Fix compatibility problems with mypy, flake8 and python 3.11

## pg\_activity 3.0.1 - 2022-09-27

### Fixed

* Fix a division by zero where there is no swap (#318, reported by @iuridiniz)

## pg\_activity 3.0.0 - 2022-09-16

### Removed

* Drop support for Python 3.6
* Attr 18.1 is required
* Replace `--query-display-mode` option by `--wrap-query` flag

### Added

* Add more information to the header (instance and process stats) (Tests
  by @Krysztophe)
* Add the `--refresh` option to the CLI to set the refresh rate (#293, suggested
  by @crysman)
* Add the `--debug-file` option to enable logging (still mostly unused)
* Add hints about runtime disabled features (#300, reported by @rutchkiwi)
* The SUPERUSER privilege is not longer required (#277, suggested by
  @Raymondmax)

### Fixed

* Add the `--no-walreceiver` to disable WAL receiver stats for Aurora
  (#301, reported by @grutz)
* Add the `--no-tempfiles` option to disable temp file statistics and
  add it to the `--rds` command (#303, reported by @adityabaradwaj)
* Fix server information queries for v12/v13 (reported and fixed by
  @kmoppel-cognite)
* Fix `InvalidTextRepresentation` errors (#275, proposed by @ssharunas)
* Fix sort order for parallel queries (#297, reported and fixed by
  @kmoppel-cognite)

### Misc.

* Doc fixes and packaging improvements (@kianmeng, @Vampouille)

**Full Changelog**: https://github.com/dalibo/pg_activity/compare/v2.3.1...v3.0.0

## pg\_activity 2.3.1 - 2022-04-28

### Fixed

* compatibility with attrs older than 18.1 #285

## pg\_activity 2.3.0 - 2022-02-09

### Fixed

* Fix encoding errors when some database encoding is not UTF-8 (#212)
* Fix blocking the query tab for multiple blockers (#241)
* Avoid refreshing the header in pause/interactive (#248)
* Fix various scrolling issues (#247)
* Fix IOW status (#252)
* Fix typo in man page (#238)

### Added

* Handle scrolling with PAGE\_UP/PAGE\_DOWN and HOME/END (#251)
* Introduce a new `--filter` option (#256)

### Changed

* Remove trailing commas after system information in header (#255)
* Document authentication (#254)
* Add missing column qualifier for dbname (#263)
* Improve performance during refresh (#249)

### Deprecated

* Support for Python 3.6 will be dropped in next release.

**Full Changelog**: https://github.com/dalibo/pg_activity/compare/v2.2.1...v2.3.0

## pg\_activity 2.2.0 - 2021-08-05

### Changed

* Display the wait_event, when available, in running and blocking queries
* Display `virtualxid` locks in blocking queries
* Gracefully handle keyboard interrupt (SIGINT)
* Rename `--verbose-mode` option as `-w/--query-display-mode` (#189)

### Fixed

* Remove random spaces from queries that wrap (#208)
* Fix a possibly `TypeError` when computing size growth (#233)
* Fix version decoding for pg >= 10 (#200)

### Misc.

* Rework the header part of the UI (more compact and extensible)
* Update the man page
* Let the man page be installed by pip
* Prevent usage of attrs version 21.1 package

## pg\_activity 2.1.5 - 2021-04-19

### Fixed

* Fix tests for Python 3.10a7 (#205)

### Misc.

* Use Github actions for CI

## pg\_activity 2.1.4 - 2021-04-02

### Changed

* Produce nicer error messages for DSN syntax errors
* Handle replication connection (with a `NULL` datname) correctly (#203)

## pg\_activity 2.1.3 - 2021-03-16

### Fixed

* Define pg\_activity script as an entry point, fixing installation in
  virtualenvs and `/usr/local` in particular (#197, #196) 

### Added

* Add support for running as `python -m pgactivity`

## pg\_activity 2.1.2 - 2021-03-12

### Fixed

* Fix test issues with Python 3.10 (#194)

### Misc.

* Add python-3.10-dev to travis test matrix

## pg\_activity 2.1.1 - 2021-03-11

### Fixed

* Document requirement on psycopg2 version
* Fix query name for 'get_active_connections' (#190)

## pg\_activity 2.1.0 - 2021-03-08

### Fixed

* Update man page to mention `<connection string>` argument

### Added

* Try to reconnect indefinitely when connection is lost
* Add a `--hide-queries-in-logs` option to hide pg\_activity's queries from
  server logs

### Changed

* Use yellow instead of orange for `PAUSE`
* Move SQL queries from Python code to individual SQL files
* Truncate long database names on Python side
* Do not display IDLE queries as None for old postgresql versions
* Let libpq handle default values for connection options (hostname, port,
  database name and user name)
* Set `application_name='pg_activity'` for client connections

## pg\_activity 2.0.3 - 2021-01-27

### Fixed

* Fix sorting logic when the duration field is None (#168)

## pg\_activity 2.0.2 - 2021-01-22

### Fixed

* Handle absence of some fields in memory info on OSX (#165)
* Handle 'query' field possibly being empty when display processes (#165)

## pg\_activity 2.0.0 - 2021-01-18

### Added

* Add a connection string argument (#151, #147)
* Clear screen when exiting help and avoid clearing the screen when not needed
* Handle reconnection to postgres

### Fixed

* Handle ZeroDivisionError in Data.pg_get_db_info()

### Misc.

* Update screenshot in README

## pg\_activity 2.0.0a3 - 2020-12-11

### Fixed

* Fix compatibility issue with old blessed version in help
* Avoid screen refresh when in help view

### Removed

* Drop --debug option, no longer handled

## pg\_activity 2.0.0a2 - 2020-11-30

### Fixed

* Ensure compatibility with older blessed version (1.15)
* Update man page
* Set shebang to use python3 in main script

## pg\_activity 2.0.0a1 - 2020-11-27

### Added

* Let k/j keys scroll the process list in interactive mode (#145)
* Improve confirmation dialog for interactive actions (#145)
* Add user and client columns in blocking and waiting queries mode (#145)
* Add a `--no-pid` option flag (#145)

### Changed

* Change keys to cancel ('C') and terminate ('K') a process in interactive mode (#145)

### Removed

* Require Python >= 3.6 (#145)
* Drop support for color de-activation (#145)
* Drop compatibility for ancient psutil versions (#145)

### Misc.

* Rewrite the UI, clean up many things (#145)
* Add type hints, checked with mypy (#145)
* Add tests, run with Python 3.6 to 3.9 in Travis-CI (#145)
* Update installation instructions (#152)
* Change author information and project URL to Dalibo (#152)
* Declare the license correctly in setup.py (#152)
* Add more classifiers for PyPI (#152)
* Add keywords for PyPI (#152)

## pg\_activity 1.6.2 - 2020-09-25

### Fixed

* Fix problems with versions of PostgreSQL older than 9.2. With this release of
  PostgreSQL, the column state was added in pg_stat_activity. The column
  current_query was also renamed to query. (by @blogh)

## pg\_activity 1.6.1 - 2020-05-14

### Fixed

* Issue #139 about duration mode for v11+ (@blogh)

## pg\_activity 1.6.0 - 2020-05-06

### Added

* Add the --min-duration flag to only show laggy queries (@kmoppel)
* Add the --duration-mode and the shortcut (T) to choose the duration modes:
  query, transaction, backend (@nilshamerlinck)
* Add a refresh dbsize interactive action shortcut (D) (Fabio Renato Geiss)
* Add --verbose-mode in man page (@julmon)

### Changed

* Move to dalibo labs (@daamien)
* Expand current 1-3s refresh interval to 0.5-5s (@kmoppel)

### Fixed

* #130: change the handling of parallel workers and fix a problem with PoWA
  (fix: @blogh @julmon, report: @debnet)
* #118: psycopg2 has to be installed manually before pg\_activity (fix: @blogh,
  report: @kmoppel)
* issue with undefined `debug` variable (@pensnarik)
* #119: some columns have been shifted in Waiting / Blocking views (fix:
  @julmon, report: @kmoppel)
* #113: Do not try to display query duration if not there (fix: @julmon, report:
  @pmpetit)

## pg\_activity 1.5.0 - 2019-03-03

### Added

* Add active connections to summary (@crisnamurti)
* Add application\_name (@michelmilezzi)
* Add PGSERVICE support (@julmon)
* New option to avoid total db sizes (@nseinlet)
* New option to change queries display mode on start (Fabio Renato Geiss)
* Save running queries list as CSV with --output option (@julmon)
* Try to reconnect to PostgreSQL cluster (@julmon)

### Changed

* Doc update about system info + examples (@Krysztophe)
* More consistent version comparison (@nseinlet)

### Fixed

* #76: cast client column to text and return 'local' if null (@julmon)
* #75: state column does not exist with postgres prior to 9.2 (@julmon)
* #74: ignore psutil warnings when fetching memory stats (@julmon)

## pg\_activity 1.4.0 - 2017-11-14

### Added

* Support of new PostgreSQL version format (@fabriziomello)
* PostgreSQL 10 support
* `state` column in all views (@mdelca)
* Option to cancel a backend (@fabriziomello)

### Fixed

* `process['database']` can be `None` for some maintenance processes

## pg\_activity 1.3.1 - 2016-10-04

### Added

* Support for PostgreSQL 9.6.

## pg\_activity 1.3.0 - 2015-11-26

### Added

* Python 3 support
* [Adds support for using pg\_activity with Amazon RDS](https://github.com/julmon/pg_activity/pull/45).
* [Handle PGUSER, PGPORT and PGHOST environment variables](https://github.com/julmon/pg_activity/pull/41).
* [Display database name in header](https://github.com/julmon/pg_activity/pull/43).

### Fixed

* [Deprecation: warning get_memory_percent() is
  deprecated](https://github.com/julmon/pg_activity/issues/39).
* New way of checking privileges of the system user running pg\_activity
  (https://github.com/julmon/pg_activity/commit/1f195b8f0cc84093129113da2e2e0ac2c3a982c9,
  https://github.com/julmon/pg_activity/commit/cca010cf35384e36ea801f9af5bc91f839596392).

## pg\_activity 1.2.0 - 2014-07-10

### Fixed

* psutils v2 API support.
* #33: Catch also TypeError error when trying to fetch process name.
* #13: Man page is not installed by default, have to use option --with-man.
* bug fix on infinite recursion loop due to bad method wrapping. 

## pg\_activity 1.1.1 - 2014-01-07

### Fixed

* crash in degraded mode due to a typo.

## pg\_activity 1.1.0 - 2013-12-04

### Fixed

* remove USER column header in WAITING and BLOCKING views
* an error was thrown on WAITING/BLOCKING views with some old psycopg2 versions

### Added

* tag/untag process
* capability to terminate all tagged backend at the same time
* new option: --blocksize=BLOCKSIZE (default: 4096), used by IOPS counting

### Changed

* code separation between data extraction and UI
* new way for IOPS counting: only reads & writes done by postgresql backends are
  considered
* change license to PostgreSQL License model

<!--
   vim: spelllang=en spell
   -->
