# Release HOW TO

## Preparatory changes

* Review the **Unreleased** section, if any, in `CHANGELOG.md` possibly adding
  any missing item from closed issues, merged pull requests, or directly the git
  history[^git-changes],
* Rename the **Unreleased** section according to the version to be released,
  with a date,
* Bump the version in `pgactivity/__init__.py`,
* Rebuild the man page, and,
* Commit these changes (either on a dedicated branch, before submitting a pull
  request or directly on the `master` branch).
* Then, when changes landed in the `master` branch, create an annotated (and
  possibly signed) tag, as `git tag -a [-s] -m 'pg_activity 1.6.0' v1.6.0`, and,
* Push with `--follow-tags`.

[^git-changes]: Use `git log $(git describe --tags --abbrev=0).. --format=%s
  --reverse` to get commits from the previous tag.

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
