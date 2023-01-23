# Release HOW TO

## Git

* Write a new change log section, for instance from closed issues, merged pull
  requests, or directly the git history (e.g. `git log $(git describe --tags
  --abbrev=0).. --format=%s --reverse` to get commits from the previous tag)
* Bump version in `pgactivity/__init__.py`, rebuild the man page
* Commit these changes on the `master` branch
* Create an annotated (and possibly signed) tag, as
  `git tag -a [-s] -m 'pg_activity 1.6.0' v1.6.0`
* Push with `--follow-tags`

## PyPI package

This requires no special action as, upon push of a tag on GitHub, the "publish"
workflow will build the Python package and upload to PyPI.

## GitHub release

*Draft a new release* from [release page][], choosing the tag just pushed and
copy respective change log section as a description.

[release page]: https://github.com/dalibo/pg_activity/releases

## Create a news article on postgresql.org and submit it

Example for release 1.6.0 : 
```
pg_activity (https://github.com/dalibo/pg_activity) 1.6.0 has been released.

This release adds the following features :

* the --min-duration flag to only show laggy queries (kmoppel)
* the --duration-mode and the shortcut (T) to choose from the duration modes:
  query, transaction, backend (nilshamerlinck)
* the D shortcut to refresh dbsize (Fabio Renato Geiss)
* an expanded refresh interval from 1-3s to 0.5-5s (kmoppel)

The full release notes can be read here :
https://github.com/dalibo/pg_activity/releases/tag/v1.6.0
