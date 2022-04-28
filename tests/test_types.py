from pgactivity.types import Filters, Flag


def test_flag():
    f = Flag(3)
    assert f == Flag.APPNAME | Flag.DATABASE
    assert f | Flag.CLIENT == Flag.CLIENT | Flag.APPNAME | Flag.DATABASE
    f ^= Flag.APPNAME
    assert f == Flag.DATABASE


def test_flag_from_options():
    options = {
        "noappname": False,
        "noclient": False,
        "nocpu": False,
        "nodb": False,
        "nomem": False,
        "nopid": False,
        "noread": False,
        "notime": False,
        "nouser": False,
        "nowait": False,
        "nowrite": False,
    }
    flag = Flag.from_options(is_local=True, **options)
    assert (
        flag
        == Flag.PID
        | Flag.IOWAIT
        | Flag.MODE
        | Flag.TYPE
        | Flag.RELATION
        | Flag.WAIT
        | Flag.TIME
        | Flag.WRITE
        | Flag.READ
        | Flag.MEM
        | Flag.CPU
        | Flag.USER
        | Flag.CLIENT
        | Flag.APPNAME
        | Flag.DATABASE
    )
    flag = Flag.from_options(is_local=False, **options)
    assert (
        flag
        == Flag.PID
        | Flag.MODE
        | Flag.TYPE
        | Flag.RELATION
        | Flag.WAIT
        | Flag.TIME
        | Flag.USER
        | Flag.CLIENT
        | Flag.APPNAME
        | Flag.DATABASE
    )
    options["nodb"] = True
    options["notime"] = True
    options["nopid"] = True
    flag = Flag.from_options(is_local=False, **options)
    assert (
        flag
        == Flag.MODE
        | Flag.TYPE
        | Flag.RELATION
        | Flag.WAIT
        | Flag.USER
        | Flag.CLIENT
        | Flag.APPNAME
    )


def test_filters_from_options():
    f = Filters.from_options(["dbname:postgres"])
    assert f == Filters(dbname="postgres")
