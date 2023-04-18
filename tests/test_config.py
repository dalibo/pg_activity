from pgactivity.config import Configuration, Flag, UISection


def test_flag():
    f = Flag(3)
    assert f == Flag.APPNAME | Flag.DATABASE
    assert f | Flag.CLIENT == Flag.CLIENT | Flag.APPNAME | Flag.DATABASE
    f ^= Flag.APPNAME
    assert f == Flag.DATABASE


def test_flag_load():
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
    flag = Flag.load(None, is_local=True, **options)
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
    cfg = Configuration(pid=UISection(hidden=True), relation=UISection(hidden=False))
    flag = Flag.load(cfg, is_local=False, **options)
    assert (
        flag
        == Flag.MODE
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
    cfg = Configuration(
        database=UISection(hidden=False), relation=UISection(hidden=True)
    )
    flag = Flag.load(cfg, is_local=False, **options)
    assert (
        flag
        == Flag.MODE | Flag.TYPE | Flag.WAIT | Flag.USER | Flag.CLIENT | Flag.APPNAME
    )
