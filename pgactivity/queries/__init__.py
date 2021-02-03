import functools
import pathlib

here = pathlib.Path(__file__).parent


@functools.lru_cache(maxsize=None)
def get(name: str) -> str:
    path = here / f"{name}.sql"
    if not path.exists():
        raise ValueError(name)
    with path.open() as f:
        return f.read()
