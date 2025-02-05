from __future__ import annotations

from pathlib import Path
from typing import Any

import attr
import pytest

from pgactivity.config import Configuration, ConfigurationError, Flag, UISection


def test_flag() -> None:
    f = Flag(3)
    assert f == Flag.APPNAME | Flag.DATABASE
    assert f | Flag.CLIENT == Flag.CLIENT | Flag.APPNAME | Flag.DATABASE
    f ^= Flag.APPNAME
    assert f == Flag.DATABASE


def test_flag_load() -> None:
    options = {
        "appname": True,
        "client": True,
        "cpu": True,
        "database": True,
        "mem": True,
        "pid": None,
        "read": True,
        "relation": True,
        "time": True,
        "user": True,
        "wait": None,
        "write": True,
        "xmin": True,
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
        | Flag.XMIN
    )
    cfg = Configuration(
        name="test",
        values=dict(
            pid=UISection(hidden=True),
            relation=UISection(hidden=False),
            wait=UISection(hidden=False),
        ),
    )
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
        | Flag.XMIN
    )
    options["database"] = False
    options["time"] = False
    options["pid"] = False
    cfg = Configuration(
        name="test",
        values=dict(database=UISection(hidden=False), relation=UISection(hidden=True)),
    )
    flag = Flag.load(cfg, is_local=False, **options)
    assert (
        flag
        == Flag.MODE
        | Flag.TYPE
        | Flag.WAIT
        | Flag.USER
        | Flag.CLIENT
        | Flag.APPNAME
        | Flag.XMIN
    )


def asdict(cfg: Configuration) -> dict[str, Any]:
    return {k: attr.asdict(v) for k, v in cfg.items()}


def test_error() -> None:
    cfg = Configuration(name="test", values={})
    with pytest.raises(ConfigurationError, match="test error") as cm:
        raise cfg.error("test error")
    assert cm.value.filename == "test"


def test_lookup(tmp_path: Path) -> None:
    cfg = Configuration.lookup(None, user_config_home=tmp_path)
    assert cfg is None

    (tmp_path / "pg_activity.conf").write_text(
        "\n".join(
            [
                "[client]",
                "width=5",
                "color=cyan",
                "[header]",
                "show_instance=no",
            ]
        )
    )
    cfg = Configuration.lookup(None, user_config_home=tmp_path)
    assert cfg is not None and asdict(cfg) == {
        "client": {"hidden": False, "width": 5, "color": "cyan"},
        "header": {"show_instance": False, "show_system": True, "show_workers": True},
    }

    (tmp_path / "pg_activity").mkdir()
    (tmp_path / "pg_activity" / "x.conf").write_text(
        "\n".join(
            ["[database]", "hidden= on", "width = 3 ", "[header]", "show_workers=no"]
        )
    )
    cfg = Configuration.lookup("x", user_config_home=tmp_path)
    assert cfg is not None and asdict(cfg) == {
        "database": {"hidden": True, "width": 3, "color": None},
        "header": {"show_instance": True, "show_system": True, "show_workers": False},
    }

    with pytest.raises(FileNotFoundError):
        Configuration.lookup("y", user_config_home=tmp_path)


no_header = {
    "header": {k: False for k in ("show_instance", "show_system", "show_workers")}
}
columns = (
    "database",
    "user",
    "client",
    "cpu",
    "mem",
    "read",
    "write",
    "appname",
    "xmin",
)
narrow = {k: {"hidden": True, "width": None, "color": None} for k in columns}
wide = {k: {"hidden": False, "width": None, "color": None} for k in columns}
minimal = {**no_header, **narrow}


@pytest.mark.parametrize(
    "profile, expected",
    [
        ("minimal", minimal),
        ("narrow", narrow),
        ("wide", wide),
    ],
)
def test_lookup_builtin_profiles(
    tmp_path: Path, profile: str, expected: dict[str, Any]
) -> None:
    cfg = Configuration.lookup(profile, user_config_home=tmp_path)
    assert cfg is not None and asdict(cfg) == expected
