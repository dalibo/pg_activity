import configparser
import enum
import os
from pathlib import Path
from typing import IO, Any, Dict, List, Optional, Type, TypeVar

import attr
from attr import validators

from .compat import gt


class ConfigurationError(Exception):
    def __init__(self, filename: str, *args: Any) -> None:
        super().__init__(*args)
        self.filename = filename

    @property
    def message(self) -> str:
        return super().__str__()

    def __str__(self) -> str:
        return f"invalid configuration '{self.filename}': {self.message}"


class InvalidSection(ConfigurationError):
    def __init__(self, section: str, *args: Any) -> None:
        super().__init__(*args)
        self.section = section

    @property
    def message(self) -> str:
        return f"invalid section '{self.section}'"


class InvalidOptions(ConfigurationError):
    def __init__(self, section: str, message: str, *args: Any) -> None:
        super().__init__(*args)
        self.section = section
        self._message = message

    @property
    def message(self) -> str:
        return f"invalid option(s) in '{self.section}': {self._message}"


class Flag(enum.Flag):
    """Column flag.

    >>> Flag.names()
    ['database', 'appname', 'client', 'user', 'cpu', 'mem', 'read', 'write', 'time', 'wait', 'relation', 'type', 'mode', 'iowait', 'pid']
    >>> Flag.all()  # doctest: +ELLIPSIS
    <Flag...: 32767>
    """

    DATABASE = enum.auto()
    APPNAME = enum.auto()
    CLIENT = enum.auto()
    USER = enum.auto()
    CPU = enum.auto()
    MEM = enum.auto()
    READ = enum.auto()
    WRITE = enum.auto()
    TIME = enum.auto()
    WAIT = enum.auto()
    RELATION = enum.auto()
    TYPE = enum.auto()
    MODE = enum.auto()
    IOWAIT = enum.auto()
    PID = enum.auto()

    @classmethod
    def names(cls) -> List[str]:
        rv = []
        for f in cls:
            assert f.name
            rv.append(f.name.lower())
        return rv

    @classmethod
    def all(cls) -> "Flag":
        value = cls(0)
        for f in cls:
            value |= f
        return value

    @classmethod
    def from_config(cls, config: "Configuration") -> "Flag":
        value = cls(0)
        for f in cls:
            assert f.name is not None
            try:
                cfg = config[f.name.lower()]
            except KeyError:
                pass
            else:
                if cfg.hidden:
                    continue
            value |= f
        return value

    @classmethod
    def load(
        cls,
        config: Optional["Configuration"],
        *,
        is_local: bool,
        noappname: bool,
        noclient: bool,
        nocpu: bool,
        nodb: bool,
        nomem: bool,
        nopid: bool,
        noread: bool,
        notime: bool,
        nouser: bool,
        nowait: bool,
        nowrite: bool,
        **kwargs: Any,
    ) -> "Flag":
        """Build a Flag value from command line options."""
        if config:
            flag = cls.from_config(config)
        else:
            flag = cls.all()
        if nodb:
            flag ^= cls.DATABASE
        if nouser:
            flag ^= cls.USER
        if nocpu:
            flag ^= cls.CPU
        if noclient:
            flag ^= cls.CLIENT
        if nomem:
            flag ^= cls.MEM
        if noread:
            flag ^= cls.READ
        if nowrite:
            flag ^= cls.WRITE
        if notime:
            flag ^= cls.TIME
        if nowait:
            flag ^= cls.WAIT
        if noappname:
            flag ^= cls.APPNAME
        if nopid:
            flag ^= cls.PID

        # Remove some if no running against local pg server.
        if not is_local and (flag & cls.CPU):
            flag ^= cls.CPU
        if not is_local and (flag & cls.MEM):
            flag ^= cls.MEM
        if not is_local and (flag & cls.READ):
            flag ^= cls.READ
        if not is_local and (flag & cls.WRITE):
            flag ^= cls.WRITE
        if not is_local and (flag & cls.IOWAIT):
            flag ^= cls.IOWAIT
        return flag


@attr.s(auto_attribs=True, frozen=True, slots=True)
class UISection:
    hidden: bool = False
    width: Optional[int] = attr.ib(default=None, validator=validators.optional(gt(0)))

    _T = TypeVar("_T", bound="UISection")

    @classmethod
    def from_config_section(cls: Type[_T], section: configparser.SectionProxy) -> _T:
        values: Dict[str, Any] = {}
        known_options = {f.name: f for f in attr.fields(cls)}
        unknown_options = set(section) - set(known_options)
        if unknown_options:
            raise ValueError(f"invalid option(s): {', '.join(sorted(unknown_options))}")
        for opt, getter in (("hidden", section.getboolean), ("width", section.getint)):
            try:
                values[opt] = getter(opt)
            except configparser.NoOptionError:
                pass
        return cls(**values)


class Configuration(Dict[str, UISection]):
    _name: str = "pg_activity.conf"
    _user_file = (
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / _name
    )
    _system_file = Path("/etc") / _name

    _T = TypeVar("_T", bound="Configuration")

    @classmethod
    def parse(cls: Type[_T], f: IO[str], name: str) -> _T:
        r"""Parse configuration from 'f'.

        >>> from io import StringIO

        >>> f = StringIO('[client]\nhidden=true\n')
        >>> Configuration.parse(f, "f.ini")
        {'client': UISection(hidden=True, width=None)}

        >>> bad = StringIO("[global]\nx=1")
        >>> Configuration.parse(bad, "bad.ini")
        Traceback (most recent call last):
          ...
        pgactivity.config.InvalidSection: invalid configuration 'bad.ini': invalid section 'global'
        >>> bad = StringIO("[xxx]\n")
        >>> Configuration.parse(bad, "bad.ini")
        Traceback (most recent call last):
          ...
        pgactivity.config.InvalidSection: invalid configuration 'bad.ini': invalid section 'xxx'
        >>> bad = StringIO("[cpu]\nx=1")
        >>> Configuration.parse(bad, "bad.ini")
        Traceback (most recent call last):
          ...
        pgactivity.config.InvalidOptions: invalid configuration 'bad.ini': invalid option(s) in 'cpu': invalid option(s): x
        >>> bad = StringIO("[mem]\nwidth=-2")
        >>> Configuration.parse(bad, "bad.ini")
        Traceback (most recent call last):
          ...
        pgactivity.config.InvalidOptions: invalid configuration 'bad.ini': invalid option(s) in 'mem': 'width' must be > 0: -2
        >>> bad = StringIO("[mem]\nwidth=xyz")
        >>> Configuration.parse(bad, "bad.ini")
        Traceback (most recent call last):
          ...
        pgactivity.config.InvalidOptions: invalid configuration 'bad.ini': invalid option(s) in 'mem': invalid literal for int() with base 10: 'xyz'
        >>> bad = StringIO("not some INI??")
        >>> Configuration.parse(bad, "bad.txt")
        Traceback (most recent call last):
          ...
        pgactivity.config.ConfigurationError: invalid configuration 'bad.txt': failed to parse INI: File contains no section headers.
        file: '<???>', line: 1
        'not some INI??'
        """
        p = configparser.ConfigParser(default_section="global", strict=True)
        try:
            p.read_file(f)
        except configparser.Error as e:
            raise ConfigurationError(name, f"failed to parse INI: {e}") from None
        known_sections = set(Flag.names())
        config = {}
        for sname, section in p.items():
            if sname == p.default_section:
                if section:
                    raise InvalidSection(p.default_section, name)
                continue
            if sname not in known_sections:
                raise InvalidSection(sname, name)
            try:
                config[sname] = UISection.from_config_section(section)
            except ValueError as e:
                raise InvalidOptions(sname, str(e), name) from None
        return cls(**config)

    @classmethod
    def lookup(cls: Type[_T]) -> Optional[_T]:
        for fpath in (cls._user_file, cls._system_file):
            if fpath.exists():
                with fpath.open() as f:
                    value = cls.parse(f, str(fpath))
                    return value
        return None
