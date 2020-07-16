import enum

import attr


@attr.s(auto_attribs=True, frozen=True, slots=True)
class Host:
    pg_version: str
    hostname: str
    user: str
    host: str
    port: int
    dbname: str


@attr.s(auto_attribs=True, slots=True)
class DBInfo:
    total_size: int
    size_ev: int


class DurationMode(enum.IntEnum):
    query = 1
    transaction = 2
    backend = 3


@attr.s(auto_attribs=True, slots=True)
class MemoryInfo:
    percent: float
    used: int
    total: int


@attr.s(auto_attribs=True, slots=True)
class LoadAverage:
    avg1: float
    avg5: float
    avg15: float


@attr.s(auto_attribs=True, slots=True)
class IOCounters:
    read_bytes: int
    write_bytes: int
    read_count: int
    write_count: int


@attr.s(auto_attribs=True, frozen=True, slots=True)
class SystemInfo:
    memory: MemoryInfo
    swap: MemoryInfo
    load: LoadAverage
    ios: IOCounters
