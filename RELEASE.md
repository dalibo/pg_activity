# Release HOW TO

## Git

* Bump version in `pgactivity/__init__.py`, rebuild the man page
* Commit these changes on the `master` branch
* Create an annotated (and possibly signed) tag, as
  `git tag -a [-s] -m 'pg_activity 1.6.0' v1.6.0`
* Push with `--follow-tags`

## PyPI package

This requires no special action as, upon push of a tag on GitHub, the "publish"
workflow will build the Python package and upload to PyPI.

## GitHub release

Prepare the release notes, for instance from closed issues, merged pull
requests, or directly the git history (e.g. `git log $(git describe --tags
--abbrev=0).. --format=%s --reverse` to get commits from the previous tag).

Use this to *draft a new release* from [release page][], choosing the tag just
pushed.

[release page]: https://github.com/dalibo/pg_activity/releases

See for example [release 1.6.0](v1.6.0):
```
Change log:

* Add the --min-duration flag to only show laggy queries (@kmoppel)
* Add the --duration-mode and the shortcut (T) to choose the duration modes:
  query, transaction, backend (@nilshamerlinck )
* Move to dalibo labs (@daamien)
* Expand current 1-3s refresh interval to 0.5-5s (@kmoppel)
* Add a refresh dbsize interactive action shortcut (D) (Fabio Renato Geiss)
* Add --verbose-mode in man page (@julmon)

Bug fixes:

* Fix #130: change the handling of parallel workers and fix a problem with PoWA
  (fix: @blogh @julmon, report: @debnet)
* Fix #118: psycopg2 has to be installed manually before pg_activity (fix:
  @blogh, report: @kmoppel)
* Fix issue with undefined debug variable (@pensnarik)
* Fix #119: some columns have been shifted in Waiting / Blocking views (fix:
  @julmon, report: @kmoppel)
* Fix #113: Do not try to display query duration if not there (fix: @julmon,
  report: @pmpetit) 
```

[v1.6.0]: https://github.com/dalibo/pg_activity/releases/tag/v1.6.0


## Send a mail to pgsql-announce

Example for release 1.6.0 : 
```
mailto  : pgsql-announce(at)postgresql(dot)org
Subject : pg_activity release 1.6.0
Content :

pg_activity (https://github.com/dalibo/pg_activity) 1.6.0 has been released.

This release adds the following features :

* the --min-duration flag to only show laggy queries (kmoppel)
* the --duration-mode and the shortcut (T) to choose from the duration modes:
  query, transaction, backend (nilshamerlinck)
* the D shortcut to refresh dbsize (Fabio Renato Geiss)
* an expanded refresh interval from 1-3s to 0.5-5s (kmoppel)

The full release notes can be read here :
https://github.com/dalibo/pg_activity/releases/tag/v1.6.0
