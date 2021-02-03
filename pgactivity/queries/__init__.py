import functools
import pathlib

here = pathlib.Path(__file__).parent


@functools.lru_cache(maxsize=None)
def get(name: str) -> str:
    path = here / f"{name}.sql"
    with path.open() as f:
        return f.read()
