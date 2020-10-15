import optparse
import os
import socket
from typing import List, Optional, Union

import attr
from blessed import Terminal

from . import __version__, Data, activities, handlers, keys, types, utils, views


def main(
    options: optparse.Values,
    *,
    term: Optional[Terminal] = None,
    screen_delimiter: Optional[str] = None,
    render_footer: bool = True,
) -> None:
    data = Data.Data()
    refresh_time = 2.0
    min_duration = data.min_duration = options.minduration
    utils.pg_connect(
        data,
        options,
        password=os.environ.get("PGPASSWORD"),
        service=os.environ.get("PGSERVICE"),
    )

    pg_version = data.pg_get_version()
    data.pg_get_num_version(pg_version)
    hostname = socket.gethostname()
    fs_blocksize = options.blocksize

    host = types.Host(
        data.get_pg_version(),
        hostname,
        options.username,
        options.host,
        options.port,
        options.dbname,
    )

    is_local = data.pg_is_local() and data.pg_is_local_access()
    duration_mode = types.DurationMode(int(options.durationmode))
    verbose_mode = types.QueryDisplayMode(int(options.verbosemode))
    flag = types.Flag.from_options(is_local=is_local, **vars(options))

    if term is None:
        # Used in tests.
        term = Terminal()
    key, in_help, in_pause = None, False, False
    query_mode = types.QueryMode.activities
    sort_key = types.SortKey.default()
    skip_sizes = options.nodbsize
    queries: Union[List[types.Activity], List[types.ActivityBW]]
    queries = data.pg_get_activities()
    procs = data.sys_get_proc(queries, is_local)
    with term.fullscreen(), term.cbreak():
        pg_db_info = None
        while True:
            pg_db_info = data.pg_get_db_info(
                pg_db_info, using_rds=options.rds, skip_sizes=skip_sizes
            )
            if options.nodbsize and not skip_sizes:
                skip_sizes = True

            dbinfo = types.DBInfo(
                total_size=int(pg_db_info["total_size"]),
                size_ev=int(pg_db_info["size_ev"]),
            )
            tps = int(pg_db_info["tps"])
            active_connections = data.pg_get_active_connections()
            max_iops = 0
            memory, swap, load = activities.mem_swap_load(data)
            system_info = types.SystemInfo.default(memory=memory, swap=swap, load=load)

            if key == keys.HELP:
                in_help = True
                print(term.clear + term.home, end="")
                views.help(
                    term,
                    __version__,
                    is_local,
                    lines_counter=views.line_counter(term.height),
                )
            elif in_help and key is not None:
                in_help, key = False, None
            elif key == keys.EXIT:
                break
            elif key == keys.PAUSE:
                in_pause = not in_pause
            elif options.nodbsize and key == keys.REFRESH_DB_SIZE:
                skip_sizes = False
            elif key in (keys.REFRESH_TIME_INCREASE, keys.REFRESH_TIME_DECREASE):
                refresh_time = handlers.refresh_time(key, refresh_time)
            elif key is not None:
                query_mode = handlers.query_mode(key) or query_mode
                sort_key = handlers.sort_key_for(key, query_mode, is_local) or sort_key
                duration_mode = handlers.duration_mode(key, duration_mode)
            if not in_help:
                if not in_pause:
                    if query_mode == types.QueryMode.activities:
                        queries = data.pg_get_activities(duration_mode)
                        if is_local:
                            new_procs = data.sys_get_proc(queries, is_local)
                            (
                                io_counters,
                                pids,
                                activity_procs,
                            ) = activities.update_processes_local(
                                procs, new_procs, fs_blocksize
                            )
                            procs = new_procs
                            (
                                read_bytes_delta,
                                write_bytes_delta,
                                read_count_delta,
                                write_count_delta,
                            ) = io_counters
                            max_iops = activities.update_max_iops(
                                max_iops, read_count_delta, write_count_delta
                            )
                            memory, swap, load = activities.mem_swap_load(data)
                            system_info = attr.evolve(
                                system_info,
                                memory=memory,
                                swap=swap,
                                load=load,
                                io_read=types.IOCounter(
                                    count=read_count_delta,
                                    bytes=int(read_bytes_delta),
                                ),
                                io_write=types.IOCounter(
                                    count=write_count_delta,
                                    bytes=int(write_count_delta),
                                ),
                            )
                            acts = activity_procs
                        else:
                            acts = queries  # type: ignore # XXX

                    elif query_mode == types.QueryMode.blocking:
                        queries = data.pg_get_blocking(duration_mode)
                        acts = queries  # type: ignore # XXX

                    elif query_mode == types.QueryMode.waiting:
                        queries = data.pg_get_waiting(duration_mode)
                        acts = queries  # type: ignore # XXX

                    acts = activities.sorted(acts, key=sort_key, reverse=True)

                if options.output is not None:
                    with open(options.output, "a") as f:
                        utils.csv_write(f, map(attr.asdict, acts))

                views.screen(
                    term,
                    host=host,
                    dbinfo=dbinfo,
                    tps=tps,
                    active_connections=active_connections,
                    duration_mode=duration_mode,
                    refresh_time=refresh_time,
                    min_duration=min_duration,
                    max_iops=max_iops,
                    system_info=system_info,
                    querymode=query_mode,
                    flag=flag,
                    sort_key=sort_key,
                    activities=acts,
                    is_local=is_local,
                    verbose_mode=verbose_mode,
                    in_pause=in_pause,
                    render_footer=render_footer,
                )

            key = term.inkey(timeout=refresh_time) or None

            if screen_delimiter is not None:
                # Used in tests.
                print(term.center(f" Received key '{key}' ", fillchar=screen_delimiter))
