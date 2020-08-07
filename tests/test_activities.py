import json

from pgactivity import activities
from pgactivity.types import Process


def test_update_processes_local(shared_datadir):
    with (shared_datadir / "local-processes-input.json").open() as f:
        input_data = json.load(f)

    processes = {k: Process.deserialize(p) for k, p in input_data["processes"].items()}
    new_processes = {
        k: Process.deserialize(p) for k, p in input_data["new_processes"].items()
    }
    fs_blocksize = input_data["fs_blocksize"]

    iocounters_delta, pids, procs = activities.update_processes_local(
        processes, new_processes, fs_blocksize
    )
    (
        read_bytes_delta,
        write_bytes_delta,
        read_count_delta,
        write_count_delta,
    ) = iocounters_delta
    assert read_bytes_delta != 0
    assert write_bytes_delta != 0
    assert read_count_delta == 0
    assert write_count_delta == 0
    assert pids == [
        "6229",
        "6223",
        "6230",
        "6233",
        "6239",
        "6228",
        "6231",
        "6221",
        "6240",
        "6238",
        "6222",
        "6234",
        "6227",
        "6237",
        "6224",
        "6226",
        "6232",
        "6225",
        "6235",
    ]
    assert set(pids) == {a.pid for a in procs}
