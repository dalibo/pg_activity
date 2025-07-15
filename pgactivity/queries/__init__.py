import functools
import pathlib

here = pathlib.Path(__file__).parent


@functools.cache
def get(name: str) -> str:
    r"""Return the SQL query contained in named file, ignoring commented lines.

    >>> get('get_version')
    'SELECT version() AS pg_version;'
    >>> print(get('get_pg_activity_post_130000')[:101])
    SELECT
          a.pid AS pid,
          a.backend_xmin AS xmin,
          a.application_name AS application_name
    """
    path = here / f"{name}.sql"
    s = "-- "
    with path.open() as f:
        return "\n".join(
            line.rstrip().split(s, 1)[0]
            for line in f
            if line.strip() and not line.startswith(s)
        )
