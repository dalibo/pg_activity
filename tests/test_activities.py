import json
from unittest.mock import patch

import attr
import pytest

from pgactivity import activities
from pgactivity.types import IOCounter, LoadAverage, MemoryInfo, Process, RunningProcess


@pytest.fixture
def processes(shared_datadir):
    with (shared_datadir / "local-processes-input.json").open() as f:
        input_data = json.load(f)

    processes = {k: Process.deserialize(p) for k, p in input_data["processes"].items()}
    new_processes = {
        k: Process.deserialize(p) for k, p in input_data["new_processes"].items()
    }
    fs_blocksize = input_data["fs_blocksize"]
    return processes, new_processes, fs_blocksize


def test_update_processes_local(processes):
    processes, new_processes, fs_blocksize = processes

    iocounters_delta, pids, procs = activities.update_processes_local(
        processes, new_processes, fs_blocksize
    )
    (
        read_bytes_delta,
        write_bytes_delta,
        read_count_delta,
        write_count_delta,
    ) = iocounters_delta
    assert int(read_bytes_delta) == 0
    assert int(write_bytes_delta) == 0
    assert read_count_delta == 0
    assert write_count_delta == 0
    assert pids == [
        "6221",
        "6222",
        "6223",
        "6224",
        "6225",
        "6226",
        "6227",
        "6228",
        "6229",
        "6230",
        "6231",
        "6232",
        "6233",
        "6234",
        "6235",
        "6237",
        "6238",
        "6239",
        "6240",
    ]
    assert set(pids) == {a.pid for a in procs}


@pytest.fixture
def system_processes(processes):
    processes, new_processes, fs_blocksize = processes
    pg_processes = []
    new_system_procs = {}
    system_procs = {}

    def running_process_fields(attribute, value):
        return attribute in attr.fields(RunningProcess)

    for new_proc in new_processes.values():
        new_system_procs[new_proc.pid] = new_proc.extras
        pg_processes.append(
            RunningProcess(**attr.asdict(new_proc, filter=running_process_fields))
        )

    system_procs = {proc.pid: proc.extras for proc in processes.values()}

    return pg_processes, system_procs, new_system_procs, fs_blocksize


def test_update_processes_local2(system_processes):
    pg_processes, system_procs, new_system_procs, fs_blocksize = system_processes
    io_read, io_write, procs = activities.update_processes_local2(
        pg_processes, system_procs, new_system_procs, fs_blocksize
    )

    assert io_read == IOCounter.default()
    assert io_write == IOCounter.default()


def test_mem_swap_load() -> None:
    with patch("pgactivity.Data.Data") as data:
        data.get_mem_swap.return_value = (12.3, 34, 45, 6.7, 8, 90)
        data.get_load_average.return_value = (0.14, 0.27, 0.44)
        memory, swap, load = activities.mem_swap_load(data)
    data.get_mem_swap.assert_called_once_with()
    data.get_load_average.assert_called_once_with()
    assert memory == MemoryInfo(percent=12.3, used=34, total=45)
    assert swap == MemoryInfo(percent=6.7, used=8, total=90)
    assert load == LoadAverage(0.14, 0.27, 0.44)
