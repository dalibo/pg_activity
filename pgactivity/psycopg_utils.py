from psycopg2.extras import DictCursorBase, DictRow
from collections import OrderedDict

import logging


logger = logging.getLogger("pgactivity")


class DictDecoderCursor(DictCursorBase):
    """A cursor that keeps a list of column name -> index mappings
       the same way a DictCursor does but uses a DictDecoderRow row
       instead.
    """

    def __init__(self, *args, **kwargs):
        kwargs['row_factory'] = DictDecoderRow
        super().__init__(*args, **kwargs)
        self._prefetch = True

    def execute(self, query, vars=None):
        self.index = OrderedDict()
        self._query_executed = True
        return super().execute(query, vars)

    def callproc(self, procname, vars=None):
        self.index = OrderedDict()
        self._query_executed = True
        return super().callproc(procname, vars)

    def _build_index(self):
        if self._query_executed and self.description:
            for i in range(len(self.description)):
                self.index[self.description[i][0]] = i
            self._query_executed = False


class DictDecoderRow(DictRow):
    """A DictRow that decodes string using the encoding column of
       the table or utf-8 if the column is notpresent.
    """
    def __getitem__(self, x):
        if not isinstance(x, (int, slice)):
            x = self._index[x]
        val = super().__getitem__(x)
        if isinstance(val, memoryview):
            val = bytes(val)
        if isinstance(val, bytes):
            if self.__contains__("encoding"):
                enc = super().__getitem__(self._index["encoding"])
                enc = enc.decode("utf-8", "backslashreplace")
            else:
                enc = "utf-8"
            val = val.decode(enc, "backslashreplace")
        return val
