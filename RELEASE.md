# Release HOW TO

## Creating the pull request

* Edit the following files and change the version :
  + `pgactivity/__init__.py`
* Prepare the release notes using the [commit
  list](https://github.com/dalibo/pg_activity/commits/master)
* Submit the PR with the release notes in the description.

Example commit message from [release
1.6.0](https://github.com/dalibo/pg_activity/releases/tag/v1.6.0)

``` 
Change log:

* Add the --min-duration flag to only show laggy queries (@kmoppel)
* Add the --duration-mode and the shortcut (T) to choose the duration modes:
  query, transaction, backend (@nilshamerlinck )
* Move to dalibo labs (@daamien)
* Expand current 1-3s refresh interval to 0.5-5s (@kmoppel)
* Add a refresh dbsize interative action shortcut (D) (Fabio Renato Geiss)
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

## Creating the release on github

Once the PR is merged, the release can be created.

Choose the option "Draft a new release" from the [release
page](https://github.com/dalibo/pg_activity/releases) : 

* Input a tag version (eg, v1.6.0) ;
* Leave the target as is (master) ;
* Input the release title (eg, pg_activity 1.6.0) ;
* Add the release notes in the release description ;
* Then press  `publish release`.

## Create the release on pypi

Upon push of a tag to GitHub, the "publish" workflow will build the Python
package and upload to PyPI.

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
```

