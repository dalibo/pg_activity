import pytest
from blessed import Terminal

from pgactivity import views
from pgactivity.config import Flag
from pgactivity.types import UI, QueryMode, SortKey


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


@pytest.mark.parametrize(
    "query, is_parallel_worker, strip_comments, expected",
    [
        ("SELECT 1 -- trailing", False, False, "SELECT 1 -- trailing"),
        ("SELECT 1 -- trailing", False, True, "SELECT 1"),
        ("SELECT /* block */ 1", False, False, "SELECT /* block */ 1"),
        ("SELECT 1 /* block */", False, True, "SELECT 1"),
    ],
)
def test_format_query_strip_comments(
    query: str, is_parallel_worker: bool, strip_comments: bool, expected: str
) -> None:
    assert (
        views.format_query(
            query,
            is_parallel_worker,
            strip_comments=strip_comments,
        )
        == expected
    )


@pytest.mark.parametrize(
    "query_mode, flags",
    [
        (QueryMode.activities, Flag.PID | Flag.QUERYID),
        (
            QueryMode.waiting,
            Flag.PID
            | Flag.QUERYID
            | Flag.DATABASE
            | Flag.APPNAME
            | Flag.CLIENT
            | Flag.USER
            | Flag.RELATION
            | Flag.TYPE
            | Flag.MODE,
        ),
        (
            QueryMode.blocking,
            Flag.PID
            | Flag.QUERYID
            | Flag.DATABASE
            | Flag.APPNAME
            | Flag.CLIENT
            | Flag.USER
            | Flag.RELATION
            | Flag.TYPE
            | Flag.MODE
            | Flag.WAIT,
        ),
    ],
    ids=["activities", "waiting", "blocking"],
)
def test_columns_header_queryid(capsys, term, query_mode, flags):
    ui = UI.make(query_mode=query_mode, flag=flags)
    views.columns_header(term, ui, width=200)
    out = capsys.readouterr()[0]
    assert "QUERYID" in out
