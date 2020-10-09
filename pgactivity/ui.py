import optparse
import os
import socket
from typing import List, Union

from blessed import Terminal

from . import __version__, Data, activities, handlers, keys, types, utils, views


def main(options: optparse.Values, refresh_time: float = 2.0) -> None:
    data = Data.Data()
    utils.pg_connect(
        data,
        options,
        password=os.environ.get("PGPASSWORD"),
        service=os.environ.get("PGSERVICE"),
    )

    pg_version = data.pg_get_version()
    data.pg_get_num_version(pg_version)
    hostname = socket.gethostname()
    fs_blocksize = 4096  # TODO: update from actual value

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

    term = Terminal()
    key, in_help = None, False
    query_mode = types.QueryMode.default()
    sort_key = types.SortKey.default()
    debugger = False
    queries: Union[List[types.Activity], List[types.ActivityBW]]
    if query_mode == types.QueryMode.activities:
        queries = data.pg_get_activities()
        procs = data.sys_get_proc(queries, is_local)
    elif query_mode == types.QueryMode.blocking:
        queries = data.pg_get_blocking()
    elif query_mode == types.QueryMode.waiting:
        queries = data.pg_get_waiting()
    with term.fullscreen(), term.cbreak():
        pg_db_info = None
        while True:
            pg_db_info = data.pg_get_db_info(
                pg_db_info, using_rds=options.rds, skip_sizes=options.nodbsize
            )

            dbinfo = types.DBInfo(
                total_size=int(pg_db_info["total_size"]),
                size_ev=int(pg_db_info["size_ev"]),
            )
            tps = int(pg_db_info["tps"])
            active_connections = data.pg_get_active_connections()
            max_iops = 0  # TODO: fetch from data
            system_info = None  # TODO: fetch from data

            if key == keys.HELP:
                in_help = True
                print(term.clear + term.home, end="")
                views.help(term, __version__, is_local, limit_height=term.height)
            elif in_help and key == "q":
                in_help, key = False, None
            elif key in (keys.REFRESH_TIME_INCREASE, keys.REFRESH_TIME_DECREASE):
                refresh_time = handlers.refresh_time(key, refresh_time)
            elif key is not None:
                query_mode = handlers.query_mode(key) or query_mode
                sort_key = handlers.sort_key_for(key, query_mode, is_local) or sort_key
            if not in_help:
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
                        # TODO: see UI.__poll_activities()
                        # data.set_global_io_counters(*io_counters)
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

                views.screen(
                    term,
                    host=host,
                    dbinfo=dbinfo,
                    tps=tps,
                    active_connections=active_connections,
                    duration_mode=duration_mode,
                    refresh_time=refresh_time,
                    max_iops=max_iops,
                    system_info=system_info,
                    querymode=query_mode,
                    flag=flag,
                    sort_key=sort_key,
                    activities=acts,
                    is_local=is_local,
                    verbose_mode=verbose_mode,
                )

            if options.debug:
                # DEBUG PRINTS
                print(term.move_y(30))
                print(term.center("  DEBUG  ", fillchar="*"))
                print(f"local: {is_local}{term.clear_eol}")
                print(f"flag: {flag!r}{term.clear_eol}")
                print(f"query mode: {query_mode}{term.clear_eol}")
                print(f"sort key: {sort_key}{term.clear_eol}")
                print(f"last key: {key!r}{term.clear_eol}")
                print("*" * term.width)

            if key == keys.EXIT:
                break
            if key == keys.EXIT_DEBUG:
                debugger = True
                break

            key = term.inkey(timeout=refresh_time) or None

    if debugger:
        import pdb

        pdb.set_trace()
