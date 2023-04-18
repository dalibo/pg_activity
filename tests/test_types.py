from pgactivity.types import Filters


def test_filters_from_options():
    f = Filters.from_options(["dbname:postgres"])
    assert f == Filters(dbname="postgres")
