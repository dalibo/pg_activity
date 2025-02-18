from __future__ import annotations

import builtins
import os
import time
from collections.abc import Sequence
from typing import TypeVar
from warnings import catch_warnings, simplefilter

import attr
import psutil

from .types import (
    BlockingProcess,
    IOCounter,
    LoadAverage,
    LocalRunningProcess,
    MemoryInfo,
    RunningProcess,
    SortKey,
    SwapInfo,
    SystemProcess,
    WaitingProcess,
)


def sys_get_proc(pid: int) -> SystemProcess | None:
    """Return a SystemProcess instance matching given pid or None if access with psutil
    is not possible.
    """
    try:
        psproc = psutil.Process(pid)
        meminfo = psproc.memory_info()
        mem_percent = psproc.memory_percent()
        cpu_percent = psproc.cpu_percent(interval=0)
        cpu_times = psproc.cpu_times()
        io_counters = psproc.io_counters()
        status_iow = str(psproc.status())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

    return SystemProcess(
        meminfo=meminfo,
        io_read=IOCounter(io_counters.read_count, io_counters.read_bytes),
        io_write=IOCounter(io_counters.write_count, io_counters.write_bytes),
        io_time=time.time(),
        mem_percent=mem_percent,
        cpu_percent=cpu_percent,
        cpu_times=cpu_times,
        read_delta=0,
        write_delta=0,
        io_wait=(status_iow == psutil.STATUS_DISK_SLEEP),
        psutil_proc=psproc,
    )


def ps_complete(
    pg_processes: Sequence[RunningProcess],
    processes: dict[int, SystemProcess],
    fs_blocksize: int,
) -> tuple[list[LocalRunningProcess], IOCounter, IOCounter]:
    """Transform the sequence of 'pg_processes' (RunningProcess) as LocalRunningProcess
    with local system information from the 'processes' map. Return LocalRunningProcess
    list, as well as read and write IO counters.

    The 'processes' map is updated in place.
    """
    local_procs = []
    read_bytes_delta = 0.0
    write_bytes_delta = 0.0
    read_count_delta = 0
    write_count_delta = 0
    n_io_time = time.time()
    for pg_proc in pg_processes:
        pid = pg_proc.pid
        new_proc = sys_get_proc(pid)
        if new_proc is None:
            continue
        try:
            # Getting information from the previous loop
            proc = processes[pid]
        except KeyError:
            # No previous information about this process
            proc = new_proc
        else:
            # Update old process with new information
            mem_percent = proc.mem_percent
            cpu_percent = proc.cpu_percent
            if proc.psutil_proc is not None:
                try:
                    mem_percent = proc.psutil_proc.memory_percent()
                    cpu_percent = proc.psutil_proc.cpu_percent(interval=0)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            proc = attr.evolve(
                proc,
                io_wait=new_proc.io_wait,
                read_delta=(
                    (new_proc.io_read.bytes - proc.io_read.bytes)
                    / (n_io_time - proc.io_time)
                ),
                write_delta=(
                    (new_proc.io_write.bytes - proc.io_write.bytes)
                    / (n_io_time - proc.io_time)
                ),
                io_read=new_proc.io_read,
                io_write=new_proc.io_write,
                io_time=n_io_time,
                mem_percent=mem_percent,
                cpu_percent=cpu_percent,
            )

            # Global io counters
            read_bytes_delta += proc.read_delta
            write_bytes_delta += proc.write_delta

        processes[pid] = proc

        local_procs.append(
            LocalRunningProcess.from_process(
                pg_proc,
                cpu=proc.cpu_percent,
                mem=proc.mem_percent,
                read=proc.read_delta,
                write=proc.write_delta,
                io_wait=proc.io_wait,
            )
        )

    # store io counters
    if read_bytes_delta > 0:
        read_count_delta += int(read_bytes_delta / fs_blocksize)
    if write_bytes_delta > 0:
        write_count_delta += int(write_bytes_delta / fs_blocksize)

    io_read = IOCounter(count=read_count_delta, bytes=int(read_bytes_delta))
    io_write = IOCounter(count=write_count_delta, bytes=int(write_bytes_delta))

    return local_procs, io_read, io_write


T = TypeVar("T", RunningProcess, WaitingProcess, BlockingProcess, LocalRunningProcess)


def sorted(processes: list[T], *, key: SortKey, reverse: bool = False) -> list[T]:
    """Return processes sorted.

    >>> from ipaddress import IPv4Interface, ip_address

    PostgreSQL 13+
    >>> processes = [
    ...     LocalRunningProcess(
    ...         pid="6240",
    ...         xmin="1234",
    ...         application_name="pgbench",
    ...         database="pgbench",
    ...         user="postgres",
    ...         client=ip_address("127.0.0.2"),
    ...         cpu=0.1,
    ...         mem=0.993_254_939_413_836,
    ...         read=0.1,
    ...         write=0.282_725_318_098_656_75,
    ...         state="idle in transaction",
    ...         query="UPDATE pgbench_accounts SET abalance = abalance + 3062 WHERE aid = 1932841;",
    ...         encoding="UTF-8",
    ...         duration=0.1,
    ...         wait="ClientRead",
    ...         io_wait=False,
    ...         query_leader_pid=6240,
    ...         is_parallel_worker=False,
    ...     ),
    ...     LocalRunningProcess(
    ...         pid="6239",
    ...         xmin="2345",
    ...         application_name="pgbench",
    ...         database="pgbench",
    ...         user="postgres",
    ...         client=IPv4Interface("192.0.2.5/24"),
    ...         cpu=0.1,
    ...         mem=0.994_254_939_413_836,
    ...         read=0.1,
    ...         write=0.282_725_318_098_656_75,
    ...         state="idle in transaction",
    ...         query="UPDATE pgbench_accounts SET abalance = abalance + 141 WHERE aid = 7289374;",
    ...         encoding=None,
    ...         duration=0.1,
    ...         wait="ClientRead",
    ...         io_wait=False,
    ...         query_leader_pid=6239,
    ...         is_parallel_worker=False,
    ...     ),
    ...     LocalRunningProcess(
    ...         pid="6228",
    ...         xmin="3456",
    ...         application_name="pgbench",
    ...         database="pgbench",
    ...         user="postgres",
    ...         client=ip_address("2001:db8::"),
    ...         cpu=0.2,
    ...         mem=1.024_758_418_061_11,
    ...         read=0.2,
    ...         write=0.113_090_128_201_154_74,
    ...         state="active",
    ...         query="UPDATE pgbench_accounts SET abalance = abalance + 3062 WHERE aid = 1932841;",
    ...         encoding="UTF-8",
    ...         duration=0.1,
    ...         wait=False,
    ...         io_wait=False,
    ...         query_leader_pid=6240,
    ...         is_parallel_worker=True,
    ...     ),
    ... ]

    >>> processes = sorted(processes, key=SortKey.cpu, reverse=True)
    >>> [p.pid for p in processes]
    ['6228', '6240', '6239']
    >>> processes = sorted(processes, key=SortKey.mem)
    >>> [p.pid for p in processes]
    ['6240', '6239', '6228']

    When using the 'duration' sort key, processes are also sorted by ascending
    (query_leader_pid, is_parallel_worker).
    >>> processes = sorted(processes, key=SortKey.duration, reverse=True)
    >>> [p.pid for p in processes]
    ['6239', '6240', '6228']

    PostgreSQL 12- (query_leader_pid is None)
    >>> processes = [
    ...     LocalRunningProcess(
    ...         pid="6240",
    ...         xmin="1234",
    ...         application_name="pgbench",
    ...         database="pgbench",
    ...         user="postgres",
    ...         client=ip_address("192.168.1.2"),
    ...         cpu=0.1,
    ...         mem=0.993_254_939_413_836,
    ...         read=0.1,
    ...         write=0.282_725_318_098_656_75,
    ...         state="idle in transaction",
    ...         query="UPDATE pgbench_accounts SET abalance = abalance + 3062 WHERE aid = 1932841;",
    ...         encoding=None,
    ...         duration=0.1,
    ...         wait="ClientRead",
    ...         io_wait=False,
    ...         query_leader_pid=None,
    ...         is_parallel_worker=False,
    ...     ),
    ...     LocalRunningProcess(
    ...         pid="6239",
    ...         xmin="2345",
    ...         application_name="pgbench",
    ...         database="pgbench",
    ...         user="postgres",
    ...         client=ip_address("0000:0000:0000:0000:0000:0abc:0007:0def"),
    ...         cpu=0.1,
    ...         mem=0.994_254_939_413_836,
    ...         read=0.1,
    ...         write=0.282_725_318_098_656_75,
    ...         state="idle in transaction",
    ...         query="UPDATE pgbench_accounts SET abalance = abalance + 141 WHERE aid = 7289374;",
    ...         encoding="UTF-8",
    ...         duration=0.1,
    ...         wait="ClientRead",
    ...         io_wait=False,
    ...         query_leader_pid=None,
    ...         is_parallel_worker=False,
    ...     ),
    ...     LocalRunningProcess(
    ...         pid="6228",
    ...         xmin="3456",
    ...         application_name="pgbench",
    ...         database="pgbench",
    ...         user="postgres",
    ...         client=None,
    ...         cpu=0.2,
    ...         mem=1.024_758_418_061_11,
    ...         read=0.2,
    ...         write=0.113_090_128_201_154_74,
    ...         state="active",
    ...         query="UPDATE pgbench_accounts SET abalance = abalance + 3062 WHERE aid = 1932841;",
    ...         encoding="latin1",
    ...         duration=0.1,
    ...         wait=False,
    ...         io_wait=False,
    ...         query_leader_pid=None,
    ...         is_parallel_worker=True,
    ...     ),
    ... ]

    >>> processes = sorted(processes, key=SortKey.duration, reverse=True)
    >>> [p.pid for p in processes]
    ['6240', '6239', '6228']
    """

    # If we filter by duration, we also need to filter by ascending
    # (query_leader_pid, is_parallel_worker):
    # * for pg13+: query_leader_pid = coalesce(leader_pid, pid)
    # * for pg12-: query_leader_pid = Null / None
    # Note: parallel_worker have the same "duration" as their leader.
    if key == SortKey.duration:
        processes = builtins.sorted(
            processes,
            key=lambda p: (p.query_leader_pid, p.is_parallel_worker),
            reverse=False,
        )

    return builtins.sorted(
        processes,
        key=lambda p: getattr(p, key.name) or 0,  # TODO: avoid getattr()
        reverse=reverse,
    )


def update_max_iops(max_iops: int, read_count: float, write_count: float) -> int:
    """Update 'max_iops' value from read_count/write_count.

    >>> update_max_iops(45657, 123, 888)
    45657
    >>> update_max_iops(3, 123, 888)
    1011
    """
    return max(int(read_count + write_count), max_iops)


def get_load_average() -> tuple[float, float, float]:
    """Get load average"""
    return os.getloadavg()


def get_mem_swap() -> tuple[MemoryInfo, SwapInfo]:
    """Get memory and swap usage"""
    with catch_warnings():
        simplefilter("ignore", RuntimeWarning)
        phymem = psutil.virtual_memory()
        vmem = psutil.swap_memory()
    # 'buffers' and 'cached' attributes are not available on some systems (e.g. OSX)
    buffers = getattr(phymem, "buffers", 0)
    cached = getattr(phymem, "cached", 0)
    mem_used = phymem.total - (phymem.free + buffers + cached)
    return (
        MemoryInfo(mem_used, buffers + cached, phymem.free, phymem.total),
        SwapInfo(vmem.used, vmem.free, vmem.total),
    )


def mem_swap_load() -> tuple[MemoryInfo, SwapInfo, LoadAverage]:
    """Read memory, swap and load average from Data object."""
    memory, swap = get_mem_swap()
    load = LoadAverage(*get_load_average())
    return memory, swap, load
