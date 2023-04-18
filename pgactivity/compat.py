import sys
from typing import Any, Dict

import attr
import blessed

if sys.version_info < (3, 8):
    from importlib_metadata import version
else:
    from importlib.metadata import version

ATTR_VERSION = tuple(int(x) for x in version("attrs").split(".", 2)[:2])
BLESSED_VERSION = tuple(int(x) for x in version("blessed").split(".", 2)[:2])

if ATTR_VERSION < (18, 1):

    def fields_dict(cls: Any) -> Dict[str, Any]:
        return {a.name: a for a in cls.__attrs_attrs__}

else:
    fields_dict = attr.fields_dict


if BLESSED_VERSION < (1, 17):

    def link(term: blessed.Terminal, url: str, text: str, url_id: str = "") -> str:
        return url

else:

    def link(term: blessed.Terminal, url: str, text: str, url_id: str = "") -> str:
        return term.link(url, text, url_id=url_id)
