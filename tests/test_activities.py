import json
from collections import namedtuple
from unittest.mock import patch

import attr
import pytest

from pgactivity import activities
from pgactivity.types import (
    IOCounter,
    LoadAverage,
    MemoryInfo,
    RunningProcess,
    SystemProcess,
    SwapInfo,
)


@pytest.fixture
def system_processes(datadir):
    with (datadir / "local-processes-input.json").open() as f:
        input_data = json.load(f)

    fs_blocksize = input_data["fs_blocksize"]

    pg_processes = []
    new_system_procs = {}
    system_procs = {}

    running_process_fields = {a.name for a in attr.fields(RunningProcess)}

    def system_process(extras):
        for k in ("io_read", "io_write"):
            try:
                extras[k] = IOCounter(**extras.pop(k))
            except KeyError:
                pass
        return SystemProcess(**extras)

    for new_proc in input_data["new_processes"].values():
        new_system_procs[new_proc["pid"]] = system_process(new_proc["extras"])
        pg_processes.append(
            RunningProcess(
                **{k: v for k, v in new_proc.items() if k in running_process_fields}
            )
        )

    system_procs = {
        proc["pid"]: system_process(proc["extras"])
        for proc in input_data["processes"].values()
    }

    return pg_processes, system_procs, new_system_procs, fs_blocksize


def test_ps_complete(system_processes):
    pg_processes, system_procs, new_system_procs, fs_blocksize = system_processes

    def sys_get_proc(pid):
        return new_system_procs.pop(pid, None)

    n_system_procs = len(system_procs)

    with patch("pgactivity.activities.sys_get_proc", new=sys_get_proc):
        procs, io_read, io_write = activities.ps_complete(
            pg_processes, system_procs, fs_blocksize
        )

    assert not new_system_procs  # all new system processes consumed

    assert io_read == IOCounter.default()
    assert io_write == IOCounter.default()
    assert len(procs) == len(pg_processes)
    assert len(system_procs) == n_system_procs
    assert {p.pid for p in procs} == {
        6221,
        6222,
        6223,
        6224,
        6225,
        6226,
        6227,
        6228,
        6229,
        6230,
        6231,
        6232,
        6233,
        6234,
        6235,
        6237,
        6238,
        6239,
        6240,
    }


def test_ps_complete_empty_procs(system_processes):
    # same as test_ps_complete() but starting with an empty "system_procs" dict
    pg_processes, __, new_system_procs, fs_blocksize = system_processes

    def sys_get_proc(pid):
        return new_system_procs.pop(pid, None)

    system_procs = {}

    with patch("pgactivity.activities.sys_get_proc", new=sys_get_proc):
        procs, io_read, io_write = activities.ps_complete(
            pg_processes, system_procs, fs_blocksize
        )

    assert not new_system_procs  # all new system processes consumed

    assert io_read == IOCounter.default()
    assert io_write == IOCounter.default()
    assert len(procs) == len(pg_processes)
    assert system_procs


def test_mem_swap_load() -> None:
    pmem = namedtuple("pmem", ["total", "free", "buffers", "cached"])
    vmem = namedtuple("vmem", ["total", "free", "used"])
    with patch(
        "psutil.virtual_memory", return_value=pmem(45, 6, 6, 7)
    ) as virtual_memory, patch(
        "psutil.swap_memory", return_value=vmem(8, 6, 2)
    ) as swap_memory, patch(
        "os.getloadavg", return_value=(0.14, 0.27, 0.44)
    ) as getloadavg:
        memory, swap, load = activities.mem_swap_load()
    virtual_memory.assert_called_once_with()
    swap_memory.assert_called_once_with()
    getloadavg.assert_called_once_with()
    assert memory == MemoryInfo(total=45, used=26, free=6, buff_cached=13)
    assert swap == SwapInfo(total=8, used=2, free=6)
    assert load == LoadAverage(0.14, 0.27, 0.44)
    assert memory.pct_used == 57.77777777777778
    assert memory.pct_free == 13.333333333333334
    assert memory.pct_bc == 28.88888888888889
    assert swap.pct_used == 25.0
    assert swap.pct_free == 75.0
