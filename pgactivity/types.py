from __future__ import annotations

import enum
import functools
from collections.abc import Callable, Iterable, Iterator, Mapping, MutableSet, Sequence
from datetime import timedelta
from ipaddress import IPv4Address, IPv6Address
from typing import Any, TypeVar, Union, overload

import attr
import psutil
from attr import validators

from . import colors, compat, pg, utils
from .config import Configuration, Flag, HeaderSection, UISection


class Pct(float):
    """Used to distinguish percentage from float when displaying the header"""


T = TypeVar("T")
E = TypeVar("E", bound=enum.IntEnum)


def enum_next(e: E) -> E:
    """Return an increment value of given enum.

    >>> class Seasons(enum.IntEnum):
    ...     winter = 1
    ...     spring = 2
    ...     summer = 3
    ...     autumn = 4

    >>> enum_next(Seasons.winter).name
    'spring'
    >>> enum_next(Seasons.spring).name
    'summer'
    >>> enum_next(Seasons.autumn).name
    'winter'
    """
    return e.__class__((e.value % max(e.__class__)) + 1)


@attr.s(auto_attribs=True, frozen=True, slots=True)
class Filters:
    dbname: str | None = None

    @classmethod
    def from_options(cls, filters: Sequence[str]) -> Filters:
        fields = compat.fields_dict(cls)
        attrs = {}
        for f in filters:
            try:
                fname, regex = f.split(":", 1)
            except ValueError:
                raise ValueError(f"malformatted filter value '{f}'")
            if not regex:
                raise ValueError(f"empty regex in filter '{f}'")
            if fname in attrs:
                raise ValueError(f"got multiple filters '{fname}'")
            if fname not in fields:
                raise ValueError(f"unknown filter '{fname}'")
            attrs[fname] = regex
        return cls(**attrs)


NO_FILTER = Filters()


class SortKey(enum.Enum):
    cpu = enum.auto()
    mem = enum.auto()
    read = enum.auto()
    write = enum.auto()
    duration = enum.auto()

    @classmethod
    def default(cls) -> SortKey:
        return cls.duration


@enum.unique
class QueryMode(enum.Enum):
    activities = "running queries"
    waiting = "waiting queries"
    blocking = "blocking queries"

    @classmethod
    def default(cls) -> QueryMode:
        return cls.activities


@enum.unique
class DurationMode(enum.IntEnum):
    query = 1
    transaction = 2
    backend = 3


def if_none(default: str) -> Callable[[Any], str]:
    def transform(value: Any) -> str:
        if value is None:
            return default
        return str(value)

    return transform


@attr.s(auto_attribs=True, frozen=True, slots=True)
class Column:
    """A column in stats table.

    >>> c = Column("pid", "PID", mandatory=True, sort_key=SortKey.cpu,
    ...            min_width=6, max_width=6,
    ...            transform=lambda v: str(v)[::-1])
    >>> c.title_render()
    'PID   '
    >>> c.title_color(SortKey.cpu)
    'cyan'
    >>> c.title_color(SortKey.duration)
    'green'
    >>> c.render('1234')
    '4321  '
    >>> c.render('12345678')
    '876543'

    >>> c = attr.evolve(c, justify="right", min_width=4, max_width=5)
    >>> c.title_render()
    ' PID'
    >>> c.render('7654321')
    '12345'
    >>> c.render('21')
    '  12'
    """

    key: str = attr.ib(repr=False)
    name: str
    mandatory: bool = False
    sort_key: SortKey | None = None
    min_width: int = attr.ib(default=0, repr=False)
    max_width: int | None = attr.ib(default=None, repr=False)
    justify: str = attr.ib(
        "left", validator=validators.in_(["left", "center", "right"])
    )
    transform: Callable[[Any], str] = attr.ib(default=if_none(""), repr=False)
    default_color: str | None = attr.ib(default=None, repr=False)
    value_color: Callable[[Any], str | None] | None = attr.ib(default=None, repr=False)
    # A callable returning a color name given a cell value or None to fall back to
    # "default_color"

    _justify: Callable[[str], str] = attr.ib(init=False)

    def __attrs_post_init__(self) -> None:
        if self.justify == "left":

            def _justify(value: str) -> str:
                return value.ljust(self.min_width)[: self.max_width]

        elif self.justify == "right":

            def _justify(value: str) -> str:
                return value.rjust(self.min_width)[: self.max_width]

        elif self.justify == "center":

            def _justify(value: str) -> str:
                return value.center(self.min_width)[: self.max_width]

        object.__setattr__(self, "_justify", _justify)

    def title_render(self) -> str:
        return self._justify(self.name)

    def title_color(self, sort_by: SortKey) -> str:
        if self.sort_key == sort_by:
            return "cyan"  # TODO: define a Color enum
        return "green"

    def render(self, value: Any) -> str:
        return self._justify(self.transform(value))

    def color(self, value: Any) -> str | None:
        if callable(self.value_color):
            color = self.value_color(value)
            if color is not None:
                return color
        return self.default_color


@attr.s(auto_attribs=True, slots=True)
class UIHeader:
    """Configuration for the header of the UI."""

    show_instance: bool = True
    show_system: bool = True
    show_workers: bool = True

    @classmethod
    def make(cls, config: HeaderSection | None, **options: bool | None) -> UIHeader:
        """Return a UIHeader built from configuration and command-line options.

        Command-line options take precedence over configuration.

        >>> config = HeaderSection(show_instance=False, show_system=False)
        >>> UIHeader.make(config, show_instance=True, show_workers=False)
        UIHeader(show_instance=True, show_system=False, show_workers=False)
        """
        values = {}
        if config is not None:
            values.update(attr.asdict(config))
        values.update({k: v for k, v in options.items() if v is not None})
        return cls(**values)

    def toggle_system(self) -> None:
        """Toggle the 'show_system' attribute.

        >>> h = UIHeader()
        >>> h.show_system
        True
        >>> h.toggle_system()
        >>> h.show_system
        False
        >>> h.toggle_system()
        >>> h.show_system
        True
        """
        self.show_system = not self.show_system

    def toggle_instance(self) -> None:
        """Toggle the 'show_instance' attribute.

        >>> h = UIHeader()
        >>> h.show_instance
        True
        >>> h.toggle_instance()
        >>> h.show_instance
        False
        >>> h.toggle_instance()
        >>> h.show_instance
        True
        """
        self.show_instance = not self.show_instance

    def toggle_workers(self) -> None:
        """Toggle the 'show_workers' attribute.

        >>> h = UIHeader()
        >>> h.show_workers
        True
        >>> h.toggle_workers()
        >>> h.show_workers
        False
        >>> h.toggle_workers()
        >>> h.show_workers
        True
        """
        self.show_workers = not self.show_workers


@attr.s(auto_attribs=True, slots=True)
class UI:
    """State of the UI."""

    header: UIHeader
    columns_by_querymode: Mapping[QueryMode, tuple[Column, ...]]
    min_duration: float = 0.0
    duration_mode: DurationMode = attr.ib(
        default=DurationMode.query, converter=DurationMode
    )
    wrap_query: bool = False
    sort_key: SortKey = attr.ib(default=SortKey.default(), converter=SortKey)
    query_mode: QueryMode = attr.ib(default=QueryMode.activities, converter=QueryMode)
    refresh_time: float | int = 2
    in_pause: bool = False
    interactive_timeout: int | None = None

    @classmethod
    def make(
        cls,
        header: UIHeader | None = None,
        config: Configuration | None = None,
        flag: Flag = Flag.all(),
        *,
        max_db_length: int = 16,
        filters: Filters = NO_FILTER,
        **kwargs: Any,
    ) -> UI:
        if header is None:
            header = UIHeader.make(config.header() if config else None)

        possible_columns: dict[str, Column] = {}
        config_values = (
            {k: v for k, v in config.items() if isinstance(v, UISection)}
            if config is not None
            else {}
        )

        def add_column(
            f: Flag | str, key: str, name: str | None = None, **kwargs: Any
        ) -> None:
            if isinstance(f, Flag):
                assert f.name is not None, f"invalid flag: {flag}"
                cfgkey = f.name
            else:
                cfgkey = f
            try:
                cfg = config_values.pop(cfgkey.lower())
            except KeyError:
                pass
            else:
                assert isinstance(cfg, UISection), cfg
                if cfg.width is not None:
                    kwargs["min_width"] = kwargs["max_width"] = cfg.width
                if cfg.color is not None:
                    if kwargs.get("value_color"):
                        assert config is not None
                        raise config.error(
                            f"the color for '{name}' column (option '{key}') cannot be configured"
                        )
                    kwargs["default_color"] = cfg.color
            assert key not in possible_columns, f"duplicated key {key}"
            if isinstance(f, Flag) and not f & flag:
                return
            if name is None:
                name = cfgkey
            possible_columns[key] = Column(key=key, name=name, **kwargs)

        add_column(
            Flag.APPNAME,
            key="application_name",
            name="APP",
            min_width=16,
            max_width=16,
            justify="right",
            default_color="bold_black",
        )
        add_column(
            Flag.CLIENT,
            key="client",
            min_width=16,
            max_width=16,
            justify="right",
            transform=if_none("local"),
            default_color="cyan",
        )
        add_column(
            Flag.CPU,
            key="cpu",
            name="CPU%",
            min_width=6,
            sort_key=SortKey.cpu,
        )
        add_column(
            Flag.DATABASE,
            key="database",
            name="DATABASE(*)" if filters.dbname else "DATABASE",
            min_width=max_db_length,
            transform=functools.lru_cache(
                lambda v: utils.ellipsis(v, width=16) if v else "",
            ),
            sort_key=None,
            default_color="bold_black",
        )
        add_column(
            Flag.IOWAIT,
            key="io_wait",
            name="IOW",
            min_width=4,
            transform=utils.yn,
            value_color=colors.wait,
        )
        add_column(
            Flag.MEM,
            key="mem",
            name="MEM%",
            min_width=4,
            sort_key=SortKey.mem,
            transform=lambda v: str(round(v, 1)),
        )
        add_column(
            Flag.MODE,
            key="mode",
            min_width=16,
            max_width=16,
            justify="right",
            value_color=colors.lock_mode,
        )
        add_column(
            Flag.PID,
            key="pid",
            min_width=6,
            default_color="cyan",
        )
        add_column(
            "query",
            key="query",
            name="Query",
            min_width=2,
        )
        add_column(
            Flag.READ,
            key="read",
            name="READ/s",
            min_width=8,
            sort_key=SortKey.read,
            transform=utils.naturalsize,
        )
        add_column(
            Flag.RELATION,
            key="relation",
            min_width=9,
            max_width=9,
            justify="right",
            default_color="cyan",
        )
        add_column(
            "state",
            key="state",
            min_width=17,
            justify="right",
            transform=utils.short_state,
            value_color=colors.short_state,
        )
        add_column(
            Flag.TIME,
            key="duration",
            name="TIME+",
            min_width=9,
            justify="right",
            sort_key=SortKey.duration,
            transform=lambda v: utils.format_duration(v)[0],
            value_color=lambda v: utils.format_duration(v)[1],
        )
        add_column(
            Flag.TYPE,
            key="type",
            min_width=16,
            max_width=16,
            justify="right",
        )
        add_column(
            Flag.USER,
            key="user",
            min_width=16,
            max_width=16,
            justify="right",
            default_color="bold_black",
        )
        add_column(
            Flag.WAIT,
            key="wait",
            name="Waiting",
            min_width=16,
            max_width=16,
            justify="right",
            transform=utils.wait_status,
            value_color=colors.wait,
        )
        add_column(
            Flag.WRITE,
            key="write",
            name="WRITE/s",
            min_width=8,
            sort_key=SortKey.write,
            transform=utils.naturalsize,
        )
        add_column(
            Flag.XMIN,
            key="xmin",
            min_width=8,
            default_color="cyan",
        )

        columns_key_by_querymode: Mapping[QueryMode, list[str]] = {
            QueryMode.activities: [
                "pid",
                "xmin",
                "database",
                "application_name",
                "user",
                "client",
                "cpu",
                "mem",
                "read",
                "write",
                "duration",
                "wait",
                "io_wait",
                "state",
                "query",
            ],
            QueryMode.waiting: [
                "pid",
                "database",
                "application_name",
                "user",
                "client",
                "relation",
                "type",
                "mode",
                "duration",
                "state",
                "query",
            ],
            QueryMode.blocking: [
                "pid",
                "database",
                "application_name",
                "user",
                "client",
                "relation",
                "type",
                "mode",
                "duration",
                "wait",
                "state",
                "query",
            ],
        }

        def make_columns_for(query_mode: QueryMode) -> Iterator[Column]:
            for key in columns_key_by_querymode[query_mode]:
                try:
                    yield possible_columns[key]
                except KeyError:
                    pass

        columns_by_querymode = {qm: tuple(make_columns_for(qm)) for qm in QueryMode}
        assert (
            not config_values
        ), f"unprocessed configuration entries: {', '.join(sorted(config_values))}"
        return cls(header=header, columns_by_querymode=columns_by_querymode, **kwargs)

    def interactive(self) -> bool:
        return self.interactive_timeout is not None

    def start_interactive(self) -> None:
        """Start interactive mode.

        >>> ui = UI.make()
        >>> ui.start_interactive()
        >>> ui.interactive_timeout
        3
        """
        self.interactive_timeout = 3

    def end_interactive(self) -> None:
        """End interactive mode.

        >>> ui = UI.make()
        >>> ui.start_interactive()
        >>> ui.interactive_timeout
        3
        >>> ui.end_interactive()
        >>> ui.interactive_timeout
        """
        self.interactive_timeout = None

    def tick_interactive(self) -> None:
        """Tick timeout of interactive mode.

        >>> ui = UI.make()
        >>> ui.tick_interactive()
        Traceback (most recent call last):
            ...
        RuntimeError: cannot tick interactive mode
        >>> ui.start_interactive()
        >>> ui.interactive_timeout
        3
        >>> ui.tick_interactive()
        >>> ui.interactive_timeout
        2
        >>> ui.tick_interactive()
        >>> ui.interactive_timeout
        1
        >>> ui.tick_interactive()
        >>> ui.interactive_timeout
        >>> ui.tick_interactive()
        Traceback (most recent call last):
            ...
        RuntimeError: cannot tick interactive mode
        """
        if self.interactive_timeout is None:
            raise RuntimeError("cannot tick interactive mode")
        assert self.interactive_timeout > 0, self.interactive_timeout
        self.interactive_timeout = (self.interactive_timeout - 1) or None

    def toggle_pause(self) -> None:
        """Toggle 'in_pause' attribute.

        >>> ui = UI.make()
        >>> ui.in_pause
        False
        >>> ui.toggle_pause()
        >>> ui.in_pause
        True
        >>> ui.toggle_pause()
        >>> ui.in_pause
        False
        """
        self.in_pause = not self.in_pause

    def evolve(self, **changes: Any) -> None:
        """Return a new UI with 'changes' applied.

        >>> ui = UI.make()
        >>> ui.query_mode.value
        'running queries'
        >>> ui.evolve(query_mode=QueryMode.blocking, sort_key=SortKey.write)
        >>> ui.query_mode.value
        'blocking queries'
        >>> ui.sort_key.name
        'write'
        """
        if self.in_pause:
            return
        forbidden = set(changes) - {
            "duration_mode",
            "wrap_query",
            "sort_key",
            "query_mode",
            "refresh_time",
        }
        assert not forbidden, forbidden
        fields = attr.fields(self.__class__)
        for field_name, value in changes.items():
            field = getattr(fields, field_name)
            if field.converter:
                value = field.converter(value)
            setattr(self, field_name, value)

    def column(self, key: str) -> Column:
        """Return the column matching 'key'.

        >>> ui = UI.make()
        >>> ui.column("cpu")  # doctest: +ELLIPSIS
        Column(name='CPU%', mandatory=False, sort_key=...)
        >>> ui.column("gloups")
        Traceback (most recent call last):
          ...
        ValueError: gloups
        """
        for column in self.columns_by_querymode[self.query_mode]:
            if column.key == key:
                return column
        else:
            raise ValueError(key)

    def columns(self) -> tuple[Column, ...]:
        """Return the tuple of Column for current mode.

        >>> flag = Flag.PID | Flag.DATABASE | Flag.APPNAME | Flag.RELATION
        >>> ui = UI.make(flag=flag)
        >>> [c.name for c in ui.columns()]
        ['PID', 'DATABASE', 'APP', 'state', 'Query']
        """
        return self.columns_by_querymode[self.query_mode]


@attr.s(auto_attribs=True, frozen=True, slots=True)
class Host:
    hostname: str
    user: str
    host: str
    port: int
    dbname: str


@attr.s(auto_attribs=True, slots=True, frozen=True)
class SwapInfo:
    used: int
    free: int
    total: int

    @classmethod
    def default(cls) -> SwapInfo:
        return cls(0, 0, 0)

    @property
    def pct_used(self) -> Pct | None:
        if self.total == 0:
            # account for the zero swap case (#318)
            return None
        return Pct(self.used * 100 / self.total)

    @property
    def pct_free(self) -> Pct | None:
        if self.total == 0:
            # account for the zero swap case (#318)
            return None
        return Pct(self.free * 100 / self.total)


@attr.s(auto_attribs=True, slots=True, frozen=True)
class MemoryInfo:
    used: int
    buff_cached: int
    free: int
    total: int

    @classmethod
    def default(cls) -> MemoryInfo:
        return cls(0, 0, 0, 0)

    @property
    def pct_used(self) -> Pct | None:
        if self.total == 0:
            return None
        return Pct(self.used * 100 / self.total)

    @property
    def pct_free(self) -> Pct | None:
        if self.total == 0:
            return None
        return Pct(self.free * 100 / self.total)

    @property
    def pct_bc(self) -> Pct | None:
        if self.total == 0:
            return None
        return Pct(self.buff_cached * 100 / self.total)


@attr.s(auto_attribs=True, slots=True)
class LoadAverage:
    avg1: float
    avg5: float
    avg15: float

    @classmethod
    def default(cls) -> LoadAverage:
        return cls(0.0, 0.0, 0.0)


@attr.s(auto_attribs=True, frozen=True, slots=True)
class IOCounter:
    count: int
    bytes: int

    @classmethod
    def default(cls) -> IOCounter:
        return cls(0, 0)


@attr.s(auto_attribs=True, frozen=True, slots=True)
class SystemInfo:
    memory: MemoryInfo
    swap: SwapInfo
    load: LoadAverage
    io_read: IOCounter
    io_write: IOCounter
    max_iops: int = 0

    @classmethod
    def default(
        cls,
        *,
        memory: MemoryInfo | None = None,
        swap: SwapInfo | None = None,
        load: LoadAverage | None = None,
    ) -> SystemInfo:
        """Zero-value builder.

        >>> SystemInfo.default()  # doctest: +NORMALIZE_WHITESPACE
        SystemInfo(memory=MemoryInfo(used=0, buff_cached=0, free=0, total=0),
                   swap=SwapInfo(used=0, free=0, total=0),
                   load=LoadAverage(avg1=0.0, avg5=0.0, avg15=0.0),
                   io_read=IOCounter(count=0, bytes=0),
                   io_write=IOCounter(count=0, bytes=0), max_iops=0)
        """
        return cls(
            memory or MemoryInfo.default(),
            swap or SwapInfo.default(),
            load or LoadAverage.default(),
            IOCounter.default(),
            IOCounter.default(),
            0,
        )


@attr.s(frozen=False, auto_attribs=True, slots=True)
class FailedQueriesInfo:
    temp_file_query_failed: bool = False
    wal_receivers_query_failed: bool = False


@attr.s(frozen=True, auto_attribs=True, slots=True)
class TempFileInfo:
    temp_files: int
    temp_bytes: int


@attr.s(frozen=True, auto_attribs=True, slots=True)
class ServerInformation:
    # Fetched from the database
    xact_count: int
    insert: int
    update: int
    delete: int
    tuples_returned: int
    total_size: int
    blks_read: int
    blks_hit: int
    xact_commit: int
    xact_rollback: int
    max_dbname_length: int
    uptime: timedelta
    epoch: int  # an epoch,  used for the calculation of the tps & size_evolution
    active_connections: int
    idle: int
    idle_in_transaction: int
    idle_in_transaction_aborted: int
    total: int
    waiting: int
    max_connections: int
    autovacuum_workers: int | None
    autovacuum_max_workers: int
    logical_replication_workers: int | None
    parallel_workers: int | None
    max_logical_replication_workers: int | None
    max_parallel_workers: int | None
    max_worker_processes: int | None
    max_wal_senders: int | None
    max_replication_slots: int | None
    wal_senders: int | None
    wal_receivers: int | None
    replication_slots: int | None
    temporary_file: TempFileInfo | None
    # Computed in data.pg_get_server_information()
    size_evolution: float
    tps: int
    insert_per_second: int
    update_per_second: int
    delete_per_second: int
    tuples_returned_per_second: int
    cache_hit_ratio_last_snap: Pct | None = attr.ib(
        converter=attr.converters.optional(Pct)
    )
    rollback_ratio_last_snap: Pct | None = attr.ib(
        converter=attr.converters.optional(Pct)
    )

    @property
    def worker_processes(self) -> int | None:
        if self.parallel_workers is None and self.logical_replication_workers is None:
            return None
        else:
            return (0 if self.parallel_workers is None else self.parallel_workers) + (
                0
                if self.logical_replication_workers is None
                else self.logical_replication_workers
            )


class LockType(enum.Enum):
    """Type of lockable object

    https://www.postgresql.org/docs/current/view-pg-locks.html
    """

    relation = enum.auto()
    extend = enum.auto()
    page = enum.auto()
    tuple = enum.auto()
    transactionid = enum.auto()
    virtualxid = enum.auto()
    object = enum.auto()
    userlock = enum.auto()
    advisory = enum.auto()

    def __str__(self) -> str:
        # Custom str(self) for transparent rendering in views.
        assert isinstance(self.name, str)
        # TODO ^ remove this assert for mypy > 0.991
        return self.name


def locktype(value: str) -> LockType:
    try:
        return LockType[value]
    except KeyError as exc:
        raise ValueError(f"invalid lock type {exc}") from None


@attr.s(auto_attribs=True, slots=True)
class BaseProcess:
    pid: int
    application_name: str
    database: str | None
    user: str
    client: None | IPv4Address | IPv6Address
    duration: float | None
    state: str
    query: str | None
    encoding: str | None
    query_leader_pid: int | None
    is_parallel_worker: bool

    _P = TypeVar("_P", bound="BaseProcess")

    @classmethod
    def from_bytes(
        cls: type[_P],
        server_encoding: bytes,
        *,
        encoding: str | bytes | None,
        **kwargs: Any,
    ) -> _P:
        if encoding is None:
            enc = server_encoding
        elif isinstance(encoding, bytes):  # psycopg2
            enc, encoding = encoding, encoding.decode()
        elif isinstance(encoding, str):
            enc = encoding.encode()
        for name, value in kwargs.items():
            if isinstance(value, bytes):
                kwargs[name] = pg.decode(value, enc, errors="replace")
        return cls(encoding=encoding, **kwargs)


@attr.s(auto_attribs=True, frozen=True, slots=True)
class RunningProcess(BaseProcess):
    """Process for a running query."""

    xmin: int
    wait: bool | None | str
    query_leader_pid: int | None
    is_parallel_worker: bool


@attr.s(auto_attribs=True, frozen=True, slots=True)
class WaitingProcess(BaseProcess):
    """Process for a waiting query."""

    # Lock information from pg_locks view
    # https://www.postgresql.org/docs/current/view-pg-locks.html
    mode: str
    type: LockType = attr.ib(converter=locktype)
    relation: str

    # TODO: update queries to select/compute these column.
    query_leader_pid: int | None = attr.ib(default=None, init=False)
    is_parallel_worker: bool = attr.ib(default=False, init=False)


@attr.s(auto_attribs=True, frozen=True, slots=True)
class BlockingProcess(BaseProcess):
    """Process for a blocking query."""

    # Lock information from pg_locks view
    # https://www.postgresql.org/docs/current/view-pg-locks.html
    mode: str
    type: LockType = attr.ib(converter=locktype)
    relation: str
    wait: bool | None | str

    # TODO: update queries to select/compute these column.
    query_leader_pid: int | None = attr.ib(default=None, init=False)
    is_parallel_worker: bool = attr.ib(default=False, init=False)


@attr.s(auto_attribs=True, frozen=True, slots=True)
class SystemProcess:
    meminfo: tuple[int, ...]
    io_read: IOCounter
    io_write: IOCounter
    io_time: float
    mem_percent: float
    cpu_percent: float
    cpu_times: tuple[float, ...]
    read_delta: float
    write_delta: float
    io_wait: bool
    psutil_proc: psutil.Process | None


@attr.s(auto_attribs=True, frozen=True, slots=True)
class LocalRunningProcess(RunningProcess):
    cpu: float
    mem: float
    read: float
    write: float
    io_wait: bool

    @classmethod
    def from_process(
        cls, process: RunningProcess, **kwargs: float | str
    ) -> LocalRunningProcess:
        return cls(**dict(attr.asdict(process), **kwargs))


@attr.s(auto_attribs=True, slots=True)
class SelectableProcesses:
    """Selectable list of processes.

    >>> @attr.s(auto_attribs=True)
    ... class Proc:
    ...     pid: int

    >>> w = SelectableProcesses(list(map(Proc, [456, 123, 789])))
    >>> len(w)
    3

    Nothing focused at initialization:
    >>> w.focused

    >>> w.focus_next()
    True
    >>> w.focused
    456
    >>> w.focus_next()
    True
    >>> w.focused
    123
    >>> _ = w.focus_next(10)
    >>> w.focused
    789
    >>> _ = w.focus_next()
    >>> w.focused
    456
    >>> _ = w.focus_next()
    >>> w.focused
    123
    >>> w.focus_prev()
    True
    >>> w.focused
    456
    >>> w.focus_prev()
    True
    >>> w.focused
    789
    >>> w.focused = 789
    >>> w.focus_next(2)
    True
    >>> w.focused
    789
    >>> w.focus_prev()
    True
    >>> w.focused
    123
    >>> _ = w.focus_prev(3)
    >>> w.focused
    456
    >>> _ = w.focus_last()
    >>> w.focused
    789
    >>> _ = w.focus_first()
    >>> w.focused
    456
    >>> w.focused = 789
    >>> _ = w.focus_prev(2)
    >>> w.focused
    456
    >>> w.focused = 789
    >>> w.set_items(sorted(w.items))
    >>> w.focused
    789
    >>> w.focus_prev()
    True
    >>> w.focused
    456
    >>> w.focus_next()
    True
    >>> w.focused
    789

    >>> w.selected, w.focused
    ([789], 789)
    >>> w.toggle_pin_focused()
    >>> w.focus_next()
    True
    >>> w.toggle_pin_focused()
    >>> w.selected, w.focused
    ([123, 789], 123)
    >>> w.toggle_pin_focused()
    >>> w.focus_next()
    True
    >>> w.toggle_pin_focused()
    >>> w.selected, w.focused
    ([456, 789], 456)

    >>> w[1]
    Proc(pid=456)
    >>> w[1:3]
    [Proc(pid=456), Proc(pid=789)]

    >>> w.reset()
    >>> w.selected, w.focused
    ([], None)

    """

    items: list[BaseProcess]
    focused: int | None = None
    pinned: MutableSet[int] = attr.ib(default=attr.Factory(set))

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[BaseProcess]:
        return iter(self.items)

    @overload
    def __getitem__(self, i: int) -> BaseProcess: ...

    @overload
    def __getitem__(self, s: slice) -> list[BaseProcess]: ...

    def __getitem__(self, val: int | slice) -> BaseProcess | list[BaseProcess]:
        return self.items[val]

    @property
    def selected(self) -> list[int]:
        if self.pinned:
            return list(self.pinned)
        elif self.focused:
            return [self.focused]
        else:
            return []

    def reset(self) -> None:
        self.focused = None
        self.pinned.clear()

    def set_items(self, new_items: Sequence[BaseProcess]) -> None:
        self.items[:] = list(new_items)

    def position(self) -> int | None:
        if self.focused is None:
            return None
        for idx, proc in enumerate(self.items):
            if proc.pid == self.focused:
                return idx
        return None

    def focus_next(self, offset: int = 1) -> bool:
        if not self.items:
            return False
        idx = self.position()
        bottom = len(self.items) - 1
        if idx is None or (offset == 1 and idx == bottom):
            next_idx = 0
        else:
            next_idx = min(bottom, idx + offset)
        self.focused = self.items[next_idx].pid
        return True

    def focus_prev(self, offset: int = 1) -> bool:
        if not self.items:
            return False
        idx = self.position() or 0
        if offset == 1:
            next_idx = idx - offset
        else:
            next_idx = max(idx - offset, 0)
        self.focused = self.items[next_idx].pid
        return True

    def focus_first(self) -> bool:
        if not self.items:
            return False
        self.focused = self.items[0].pid
        return True

    def focus_last(self) -> bool:
        if not self.items:
            return False
        self.focused = self.items[-1].pid
        return True

    def toggle_pin_focused(self) -> None:
        assert self.focused is not None
        try:
            self.pinned.remove(self.focused)
        except KeyError:
            self.pinned.add(self.focused)

    def copy_focused_query_to_clipboard(self) -> str:
        """Copy focused query to system clipboard using ANSI OSC 52 escape sequence."""
        assert self.focused is not None
        for proc in self.items:
            if proc.pid == self.focused:
                break
        else:
            return "no focused process found"
        if proc.query is None:
            return "process has no query"

        utils.osc52_copy(proc.query)
        return f"query of process {proc.pid} copied to clipboard"


ActivityStats = Union[
    Iterable[WaitingProcess],
    Iterable[RunningProcess],
    tuple[Iterable[WaitingProcess], SystemInfo],
    tuple[Iterable[BlockingProcess], SystemInfo],
    tuple[Iterable[LocalRunningProcess], SystemInfo],
]
