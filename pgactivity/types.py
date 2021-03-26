import enum
import functools
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableSet,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

import attr
import psutil

from . import colors, utils


T = TypeVar("T")


E = TypeVar("E", bound=enum.IntEnum)


def enum_next(e: E) -> E:
    """Return an increment value of given enum.

    >>> class Seasons(enum.IntEnum):
    ...     winter = 1
    ...     spring = 2
    ...     summer = 3
    ...     autumn = 4

    >>> enum_next(Seasons.winter)
    <Seasons.spring: 2>
    >>> enum_next(Seasons.spring)
    <Seasons.summer: 3>
    >>> enum_next(Seasons.autumn)
    <Seasons.winter: 1>
    """
    return e.__class__((e.value % max(e.__class__)) + 1)


@enum.unique
class Flag(enum.IntFlag):
    """Column flag."""

    DATABASE = 1
    APPNAME = 2
    CLIENT = 4
    USER = 8
    CPU = 16
    MEM = 32
    READ = 64
    WRITE = 128
    TIME = 256
    WAIT = 512
    RELATION = 1024
    TYPE = 2048
    MODE = 4096
    IOWAIT = 8192
    PID = 16384

    @classmethod
    def all(cls) -> "Flag":
        return cls(sum(cls))

    @classmethod
    def from_options(
        cls,
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


class SortKey(enum.Enum):
    cpu = enum.auto()
    mem = enum.auto()
    read = enum.auto()
    write = enum.auto()
    duration = enum.auto()

    @classmethod
    def default(cls) -> "SortKey":
        return cls.duration


@enum.unique
class QueryDisplayMode(enum.IntEnum):
    truncate = 1
    wrap_noindent = 2
    wrap = 3

    @classmethod
    def default(cls) -> "QueryDisplayMode":
        return cls.wrap_noindent


@enum.unique
class QueryMode(enum.Enum):
    activities = "running queries"
    waiting = "waiting queries"
    blocking = "blocking queries"

    @classmethod
    def default(cls) -> "QueryMode":
        return cls.activities


@enum.unique
class DurationMode(enum.IntEnum):
    query = 1
    transaction = 2
    backend = 3


_color_key_marker = f"{id(object())}"


@attr.s(auto_attribs=True, frozen=True, slots=True)
class Column:
    """A column in stats table.

    >>> c = Column("pid", "PID", "%-6s", True, SortKey.cpu, max_width=6,
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
    >>> c.color_key
    'pid'
    """

    key: str = attr.ib(repr=False)
    name: str
    template_h: str = attr.ib()
    mandatory: bool = False
    sort_key: Optional[SortKey] = None
    max_width: Optional[int] = attr.ib(default=None, repr=False)
    transform: Callable[[Any], str] = attr.ib(default=str, repr=False)
    color_key: Union[str, Callable[[Any], str]] = attr.ib(
        default=_color_key_marker, repr=False
    )

    @template_h.validator
    def _template_h_is_a_format_string_(self, attribute: Any, value: str) -> None:
        """Validate template_h attribute.

        >>> Column("k", "a", "b%%aa")
        Traceback (most recent call last):
            ...
        ValueError: template_h must be a format string with one placeholder
        >>> Column("k", "a", "baad")
        Traceback (most recent call last):
            ...
        ValueError: template_h must be a format string with one placeholder
        >>> Column("k", "a", "%s is good")  # doctest: +ELLIPSIS
        Column(name='a', template_h='%s is good', ...)
        """
        if value.count("%") != 1:
            raise ValueError(
                f"{attribute.name} must be a format string with one placeholder"
            )

    def __attrs_post_init__(self) -> None:
        if self.color_key == _color_key_marker:
            object.__setattr__(self, "color_key", self.key)

    def title_render(self) -> str:
        return self.template_h % self.name

    def title_color(self, sort_by: SortKey) -> str:
        if self.sort_key == sort_by:
            return "cyan"  # TODO: define a Color enum
        return "green"

    def render(self, value: Any) -> str:
        return self.template_h % self.transform(value)[: self.max_width]

    def color(self, value: Any) -> str:
        if callable(self.color_key):
            return self.color_key(value)
        return self.color_key


@attr.s(auto_attribs=True, slots=True)
class UI:
    """State of the UI."""

    columns_by_querymode: Mapping[QueryMode, Tuple[Column, ...]]
    min_duration: float = 0.0
    duration_mode: DurationMode = attr.ib(
        default=DurationMode.query, converter=DurationMode
    )
    verbose_mode: QueryDisplayMode = attr.ib(
        default=QueryDisplayMode.default(), converter=QueryDisplayMode
    )
    sort_key: SortKey = attr.ib(default=SortKey.default(), converter=SortKey)
    query_mode: QueryMode = attr.ib(default=QueryMode.activities, converter=QueryMode)
    refresh_time: Union[float, int] = 2
    in_pause: bool = False
    interactive_timeout: Optional[int] = None

    @classmethod
    def make(
        cls,
        flag: Flag = Flag.all(),
        *,
        max_db_length: int = 16,
        **kwargs: Any,
    ) -> "UI":
        possible_columns: Dict[str, Column] = {}

        def add_column(key: str, **kwargs: Any) -> None:
            assert key not in possible_columns, f"duplicated key {key}"
            possible_columns[key] = Column(key, **kwargs)

        if Flag.APPNAME & flag:
            add_column(
                key="application_name",
                name="APP",
                template_h="%16s ",
                max_width=16,
            )
        if Flag.CLIENT & flag:
            add_column(
                key="client",
                name="CLIENT",
                template_h="%16s ",
                max_width=16,
            )
        if Flag.CPU & flag:
            add_column(
                key="cpu",
                name="CPU%",
                template_h="%6s ",
                sort_key=SortKey.cpu,
            )
        if Flag.DATABASE & flag:
            add_column(
                key="database",
                name="DATABASE",
                template_h=f"%-{max_db_length}s ",
                transform=functools.lru_cache()(
                    lambda v: utils.ellipsis(v, width=16) if v else "",
                ),
                sort_key=None,
            )
        if Flag.IOWAIT & flag:
            add_column(
                key="io_wait",
                name="IOW",
                template_h="%4s ",
                transform=utils.yn,
                color_key=colors.wait,
            )
        if Flag.MEM & flag:
            add_column(
                key="mem",
                name="MEM%",
                template_h="%4s ",
                sort_key=SortKey.mem,
                transform=lambda v: str(round(v, 1)),
            )
        if Flag.MODE & flag:
            add_column(
                key="mode",
                name="MODE",
                template_h="%16s ",
                max_width=16,
                color_key=colors.lock_mode,
            )
        if Flag.PID & flag:
            add_column(key="pid", name="PID", template_h="%-6s ")
        add_column(key="query", name="Query", template_h=" %2s")
        if Flag.READ & flag:
            add_column(
                key="read",
                name="READ/s",
                template_h="%8s ",
                sort_key=SortKey.read,
                transform=utils.naturalsize,
            )
        if Flag.RELATION & flag:
            add_column(
                key="relation",
                name="RELATION",
                template_h="%9s ",
                max_width=9,
            )
        add_column(
            key="state",
            name="state",
            template_h=" %17s  ",
            transform=utils.short_state,
            color_key=colors.short_state,
        )
        if Flag.TIME & flag:
            add_column(
                key="duration",
                name="TIME+",
                template_h="%9s ",
                sort_key=SortKey.duration,
                transform=lambda v: utils.format_duration(v)[0],
                color_key=lambda v: utils.format_duration(v)[1],
            )
        if Flag.TYPE & flag:
            add_column(key="type", name="TYPE", template_h="%16s ", max_width=16)
        if Flag.USER & flag:
            add_column(key="user", name="USER", template_h="%16s ", max_width=16)
        if Flag.WAIT & flag:
            add_column(
                key="wait",
                name="W",
                template_h="%2s ",
                transform=utils.yn,
                color_key=colors.wait,
            )
        if Flag.WRITE & flag:
            add_column(
                key="write",
                name="WRITE/s",
                template_h="%8s ",
                sort_key=SortKey.write,
                transform=utils.naturalsize,
            )

        columns_key_by_querymode: Mapping[QueryMode, List[str]] = {
            QueryMode.activities: [
                "pid",
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
        return cls(columns_by_querymode=columns_by_querymode, **kwargs)

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
        """End interactive mode.

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
            "verbose_mode",
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
        >>> ui.column("cpu")
        Column(name='CPU%', template_h='%6s ', mandatory=False, sort_key=<SortKey.cpu: 1>)
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

    def columns(self) -> Tuple[Column, ...]:
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


@attr.s(auto_attribs=True, slots=True)
class DBInfo:
    total_size: int
    size_ev: int


@attr.s(auto_attribs=True, slots=True)
class MemoryInfo:
    percent: float
    used: int
    total: int

    @classmethod
    def default(cls) -> "MemoryInfo":
        return cls(0.0, 0, 0)


@attr.s(auto_attribs=True, slots=True)
class LoadAverage:
    avg1: float
    avg5: float
    avg15: float

    @classmethod
    def default(cls) -> "LoadAverage":
        return cls(0.0, 0.0, 0.0)


@attr.s(auto_attribs=True, frozen=True, slots=True)
class IOCounter:
    count: int
    bytes: int
    chars: int = 0

    @classmethod
    def default(cls) -> "IOCounter":
        return cls(0, 0)


@attr.s(auto_attribs=True, frozen=True, slots=True)
class SystemInfo:
    memory: MemoryInfo
    swap: MemoryInfo
    load: LoadAverage
    io_read: IOCounter
    io_write: IOCounter
    max_iops: int = 0

    @classmethod
    def default(
        cls,
        *,
        memory: Optional[MemoryInfo] = None,
        swap: Optional[MemoryInfo] = None,
        load: Optional[LoadAverage] = None,
    ) -> "SystemInfo":
        """Zero-value builder.

        >>> SystemInfo.default()  # doctest: +NORMALIZE_WHITESPACE
        SystemInfo(memory=MemoryInfo(percent=0.0, used=0, total=0),
                   swap=MemoryInfo(percent=0.0, used=0, total=0),
                   load=LoadAverage(avg1=0.0, avg5=0.0, avg15=0.0),
                   io_read=IOCounter(count=0, bytes=0, chars=0),
                   io_write=IOCounter(count=0, bytes=0, chars=0),
                   max_iops=0)
        """
        return cls(
            memory or MemoryInfo.default(),
            swap or MemoryInfo.default(),
            load or LoadAverage.default(),
            IOCounter.default(),
            IOCounter.default(),
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
    database: Optional[str]
    user: str
    client: str
    duration: Optional[float]
    state: str
    query: Optional[str]
    is_parallel_worker: bool


@attr.s(auto_attribs=True, frozen=True, slots=True)
class RunningProcess(BaseProcess):
    """Process for a running query."""

    wait: bool
    is_parallel_worker: bool


@attr.s(auto_attribs=True, frozen=True, slots=True)
class BWProcess(BaseProcess):
    """Process for a blocking or waiting query."""

    # Lock information from pg_locks view
    # https://www.postgresql.org/docs/current/view-pg-locks.html
    mode: str
    type: LockType = attr.ib(converter=locktype)
    relation: str

    # TODO: update queries to select/compute this column.
    is_parallel_worker: bool = attr.ib(default=False, init=False)


@attr.s(auto_attribs=True, frozen=True, slots=True)
class SystemProcess:
    meminfo: Tuple[int, ...]
    io_read: IOCounter
    io_write: IOCounter
    io_time: float
    mem_percent: float
    cpu_percent: float
    cpu_times: Tuple[float, ...]
    read_delta: float
    write_delta: float
    io_wait: bool
    psutil_proc: Optional[psutil.Process]


@attr.s(auto_attribs=True, frozen=True, slots=True)
class LocalRunningProcess(RunningProcess):
    cpu: float
    mem: float
    read: float
    write: float
    io_wait: bool

    @classmethod
    def from_process(
        cls, process: RunningProcess, **kwargs: Union[float, str]
    ) -> "LocalRunningProcess":
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
    >>> w.focused
    456
    >>> w.focus_next()
    >>> w.focused
    123
    >>> w.focus_prev()
    >>> w.focused
    456
    >>> w.focus_prev()
    >>> w.focused
    789
    >>> w.focused = 789
    >>> w.focus_next()
    >>> w.focused
    456
    >>> w.focus_prev()
    >>> w.focused
    789
    >>> w.set_items(sorted(w.items))
    >>> w.focused
    789
    >>> w.focus_prev()
    >>> w.focused
    456
    >>> w.focus_next()
    >>> w.focused
    789

    >>> w.selected, w.focused
    ([789], 789)
    >>> w.toggle_pin_focused()
    >>> w.focus_next()
    >>> w.toggle_pin_focused()
    >>> w.selected, w.focused
    ([123, 789], 123)
    >>> w.toggle_pin_focused()
    >>> w.focus_next()
    >>> w.toggle_pin_focused()
    >>> w.selected, w.focused
    ([456, 789], 456)
    >>> w.reset()
    >>> w.selected, w.focused
    ([], None)
    """

    items: List[BaseProcess]
    focused: Optional[int] = None
    pinned: MutableSet[int] = attr.ib(default=attr.Factory(set))

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[BaseProcess]:
        return iter(self.items)

    @property
    def selected(self) -> List[int]:
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

    def _position(self) -> Optional[int]:
        if self.focused is None:
            return None
        for idx, proc in enumerate(self.items):
            if proc.pid == self.focused:
                return idx
        return None

    def focus_next(self) -> None:
        if not self.items:
            return
        idx = self._position()
        if idx is None:
            next_idx = 0
        elif idx == len(self.items) - 1:
            next_idx = 0
        else:
            next_idx = idx + 1
        self.focused = self.items[next_idx].pid

    def focus_prev(self) -> None:
        if not self.items:
            return
        idx = self._position() or 0
        self.focused = self.items[idx - 1].pid

    def toggle_pin_focused(self) -> None:
        assert self.focused is not None
        try:
            self.pinned.remove(self.focused)
        except KeyError:
            self.pinned.add(self.focused)


ActivityStats = Union[
    Iterable[BWProcess],
    Iterable[RunningProcess],
    Tuple[Iterable[BWProcess], SystemInfo],
    Tuple[Iterable[LocalRunningProcess], SystemInfo],
]
