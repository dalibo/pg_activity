import pytest
from blessed import Terminal

from pgactivity import views
from pgactivity.types import Flag, QueryMode, SortKey, UI


@pytest.fixture
def term() -> Terminal:
    return Terminal()


@pytest.mark.parametrize(
    "ui, width, expected",
    [
        (
            UI.make(
                query_mode=QueryMode.activities,
                flag=Flag.PID | Flag.DATABASE,
                sort_key=SortKey.cpu,
            ),
            83,
            "PID    DATABASE                     state Query",
        ),
        (
            UI.make(
                query_mode=QueryMode.activities, flag=Flag.CPU, sort_key=SortKey.cpu
            ),
            None,
            "CPU%               state Query",
        ),
        (
            UI.make(
                query_mode=QueryMode.activities, flag=Flag.MEM, sort_key=SortKey.cpu
            ),
            None,
            "MEM%             state Query",
        ),
        (
            UI.make(
                query_mode=QueryMode.blocking,
                flag=Flag.PID
                | Flag.DATABASE
                | Flag.APPNAME
                | Flag.RELATION
                | Flag.CLIENT
                | Flag.WAIT,
                sort_key=SortKey.duration,
            ),
            150,
            "PID    DATABASE                      APP           CLIENT  RELATION          Waiting             state Query",
        ),
    ],
    ids=[
        "pid+database; sort by cpu; activities",
        "cpu; sort by cpu; activities",
        "mem; sort by cpu; activities",
        "many flags; sort by duration; blocking",
    ],
)
def test_columns_header(capsys, term, ui, width, expected):
    views.columns_header(term, ui, width=width)
    out = capsys.readouterr()[0]
    assert out == expected + "\n"
