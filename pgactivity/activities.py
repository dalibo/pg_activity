import builtins
import time
from typing import Dict, List, Sequence, Tuple, TypeVar

import psutil

from . import utils
from .Data import Data
from .types import (
    BWProcess,
    IOCounter,
    LoadAverage,
    LocalRunningProcess,
    MemoryInfo,
    Process,
    RunningProcess,
    SortKey,
    SystemProcess,
)


def update_processes_local2(
    pg_processes: Sequence[RunningProcess],
    processes: Dict[int, SystemProcess],
    new_processes: Dict[int, SystemProcess],
    fs_blocksize: int,
) -> Tuple[IOCounter, IOCounter, List[LocalRunningProcess]]:
    """Update resource usage for each process in *local* mode."""
    procs = []
    read_bytes_delta = 0.0
    write_bytes_delta = 0.0
    read_count_delta = 0
    write_count_delta = 0
    n_io_time = time.time()
    pg_procs_by_pids = {p.pid: p for p in pg_processes}
    for pid, new_proc in new_processes.items():
        pg_proc = pg_procs_by_pids[pid]
        try:
            try:
                # Getting informations from the previous loop
                proc = processes[pid]
            except KeyError:
                # No previous information about this process
                proc = new_proc
            else:
                # Update old process with new informations
                proc.io_wait = new_proc.io_wait
                proc.read_delta = (new_proc.io_read.bytes - proc.io_read.bytes) / (
                    n_io_time - proc.io_time
                )
                proc.write_delta = (new_proc.io_write.bytes - proc.io_write.bytes) / (
                    n_io_time - proc.io_time
                )
                proc.io_read = new_proc.io_read
                proc.io_write = new_proc.io_write
                proc.io_time = n_io_time

                # Global io counters
                read_bytes_delta += proc.read_delta
                write_bytes_delta += proc.write_delta

            if proc.psutil_proc is not None:
                proc.mem_percent = proc.psutil_proc.memory_percent()
                proc.cpu_percent = proc.psutil_proc.cpu_percent(interval=0)
            new_processes[pid] = proc
            procs.append(
                LocalRunningProcess.from_process(
                    pg_proc,
                    cpu=proc.cpu_percent,
                    mem=proc.mem_percent,
                    read=proc.read_delta,
                    write=proc.write_delta,
                    io_wait=proc.io_wait,
                )
            )

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # store io counters
    if read_bytes_delta > 0:
        read_count_delta += int(read_bytes_delta / fs_blocksize)
    if write_bytes_delta > 0:
        write_count_delta += int(write_bytes_delta / fs_blocksize)

    io_read = IOCounter(count=read_count_delta, bytes=int(read_bytes_delta))
    io_write = IOCounter(count=write_count_delta, bytes=int(write_bytes_delta))

    return io_read, io_write, procs


def update_processes_local(
    processes: Dict[int, Process], new_processes: Dict[int, Process], fs_blocksize: int
) -> Tuple[Tuple[float, float, int, int], List[int], List[LocalRunningProcess]]:
    """Update resource usage for each process in *local* mode."""
    pids = []
    procs = []
    read_bytes_delta = 0.0
    write_bytes_delta = 0.0
    read_count_delta = 0
    write_count_delta = 0
    for pid, new_proc in new_processes.items():
        try:
            if pid in processes:
                n_io_time = time.time()
                # Getting informations from the previous loop
                proc = processes[pid]
                # Update old process with new informations
                proc.duration = new_proc.duration
                proc.state = new_proc.state
                proc.query = new_proc.query
                proc.appname = new_proc.appname
                proc.client = new_proc.client
                proc.wait = new_proc.wait
                proc.extras.io_wait = new_proc.extras.io_wait
                proc.extras.read_delta = (
                    new_proc.extras.io_read.bytes - proc.extras.io_read.bytes
                ) / (n_io_time - proc.extras.io_time)
                proc.extras.write_delta = (
                    new_proc.extras.io_write.bytes - proc.extras.io_write.bytes
                ) / (n_io_time - proc.extras.io_time)
                proc.extras.io_read = new_proc.extras.io_read
                proc.extras.io_write = new_proc.extras.io_write
                proc.extras.io_time = n_io_time

                # Global io counters
                read_bytes_delta += proc.extras.read_delta
                write_bytes_delta += proc.extras.write_delta
            else:
                # No previous information about this process
                proc = new_proc

            if pid not in pids:
                pids.append(pid)

            if proc.extras.psutil_proc is not None:
                proc.extras.mem_percent = proc.extras.psutil_proc.memory_percent()
                proc.extras.cpu_percent = proc.extras.psutil_proc.cpu_percent(
                    interval=0
                )
            new_processes[pid] = proc
            procs.append(
                LocalRunningProcess(
                    pid=pid,
                    appname=proc.appname,
                    database=proc.database,
                    user=proc.user,
                    client=proc.client,
                    cpu=proc.extras.cpu_percent,
                    mem=proc.extras.mem_percent,
                    read=proc.extras.read_delta,
                    write=proc.extras.write_delta,
                    state=proc.state,
                    query=proc.query,
                    duration=utils.get_duration(proc.duration),
                    wait=proc.wait,
                    io_wait=proc.extras.io_wait,
                    is_parallel_worker=proc.is_parallel_worker,
                )
            )

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # store io counters
    if read_bytes_delta > 0:
        read_count_delta += int(read_bytes_delta / fs_blocksize)
    if write_bytes_delta > 0:
        write_count_delta += int(write_bytes_delta / fs_blocksize)

    io_counters = (
        read_bytes_delta,
        write_bytes_delta,
        read_count_delta,
        write_count_delta,
    )

    return io_counters, pids, procs


T = TypeVar("T", RunningProcess, BWProcess, LocalRunningProcess)


def sorted(processes: List[T], *, key: SortKey, reverse: bool = False) -> List[T]:
    """Return processes sorted.

    >>> processes = [
    ...     LocalRunningProcess(
    ...         pid="6239",
    ...         appname="pgbench",
    ...         database="pgbench",
    ...         user="postgres",
    ...         client="local",
    ...         cpu=0.1,
    ...         mem=0.993_254_939_413_836,
    ...         read=0.1,
    ...         write=0.282_725_318_098_656_75,
    ...         state="idle in transaction",
    ...         query="UPDATE pgbench_accounts SET abalance = abalance + 141 WHERE aid = 1932841;",
    ...         duration=0,
    ...         wait=False,
    ...         io_wait="N",
    ...         is_parallel_worker=False,
    ...     ),
    ...     LocalRunningProcess(
    ...         pid="6228",
    ...         appname="pgbench",
    ...         database="pgbench",
    ...         user="postgres",
    ...         client="local",
    ...         cpu=0.2,
    ...         mem=1.024_758_418_061_11,
    ...         read=0.2,
    ...         write=0.113_090_128_201_154_74,
    ...         state="active",
    ...         query="UPDATE pgbench_accounts SET abalance = abalance + 3062 WHERE aid = 7289374;",
    ...         duration=0,
    ...         wait=False,
    ...         io_wait="N",
    ...         is_parallel_worker=True,
    ...     ),
    ... ]

    >>> processes = sorted(processes, key=SortKey.cpu, reverse=True)
    >>> [p.pid for p in processes]
    ['6228', '6239']
    >>> processes = sorted(processes, key=SortKey.mem)
    >>> [p.pid for p in processes]
    ['6239', '6228']
    """
    return builtins.sorted(
        processes,
        key=lambda p: getattr(p, key.name),  # type: ignore  # TODO: avoid getattr()
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


def mem_swap_load(data: Data) -> Tuple[MemoryInfo, MemoryInfo, LoadAverage]:
    """Read memory, swap and load average from Data object."""
    mem_swap = data.get_mem_swap()
    memory = MemoryInfo(*mem_swap[:3])
    swap = MemoryInfo(*mem_swap[3:])
    load = LoadAverage(*data.get_load_average())
    return memory, swap, load
