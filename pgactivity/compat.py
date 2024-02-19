from __future__ import annotations

import importlib.resources
import operator
import sys
from importlib.metadata import version
from typing import Any

import attr
import attr.validators
import blessed

__all__ = [
    "Callable",
    "Dict",
    "Iterable",
    "Iterator",
    "Mapping",
    "MutableSet",
    "Sequence",
]

if sys.version_info >= (3, 9):
    from collections.abc import (
        Callable,
        Iterable,
        Iterator,
        Mapping,
        MutableSet,
        Sequence,
    )

    Dict = dict
else:
    from typing import Callable, Dict, Iterable, Iterator, Mapping, MutableSet, Sequence

if sys.version_info >= (3, 11):

    def read_resource(pkgname: str, dirname: str, *args: str) -> str | None:
        resource = importlib.resources.files(pkgname).joinpath(dirname)
        for arg in args:
            resource = resource.joinpath(arg)
        if resource.is_file():
            return resource.read_text()
        return None

else:

    def read_resource(pkgname: str, dirname: str, *args: str) -> str | None:
        with importlib.resources.path(pkgname, dirname) as dirp:
            f = dirp.joinpath(*args)
            if f.is_file():
                return f.read_text()
            return None


ATTR_VERSION = tuple(int(x) for x in version("attrs").split(".", 2)[:2])
BLESSED_VERSION = tuple(int(x) for x in version("blessed").split(".", 2)[:2])

if ATTR_VERSION < (18, 1):

    def fields_dict(cls: Any) -> dict[str, Any]:
        return {a.name: a for a in cls.__attrs_attrs__}

else:
    fields_dict = attr.fields_dict

if ATTR_VERSION < (21, 3):

    @attr.s(auto_attribs=True, frozen=True, slots=True)
    class gt:
        bound: int

        def __call__(self, instance: Any, attribute: Any, value: Any) -> None:
            if not operator.gt(value, self.bound):
                raise ValueError(f"'{attribute.name}' must be > {self.bound}: {value}")

else:
    gt = attr.validators.gt  # type: ignore[assignment,misc]


if BLESSED_VERSION < (1, 17):

    def link(term: blessed.Terminal, url: str, text: str, url_id: str = "") -> str:
        return url

else:

    def link(term: blessed.Terminal, url: str, text: str, url_id: str = "") -> str:
        return term.link(url, text, url_id=url_id)
