import optparse
import os
import socket

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

    is_local = data.pg_is_local()
    duration_mode = types.DurationMode(int(options.durationmode))
    verbose_mode = types.QueryDisplayMode(int(options.verbosemode))
    flag = types.Flag.from_options(is_local=is_local, **vars(options))

    term = Terminal()
    key, in_help = None, False
    query_mode = types.QueryMode.default()
    sort_key = types.SortKey.default()
    debugger = False
    if query_mode == types.QueryMode.activities:
        queries = data.pg_get_activities()
        procs = data.sys_get_proc(queries, is_local)
    # elif query_mode == types.QueryMode.waiting:
    #     procs = data.pg_get_waiting()
    # elif query_mode == types.QueryMode.blocking:
    #     procs = data.pg_get_blocking()
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
                views.help(term, __version__, is_local)
            elif in_help and key == "q":
                in_help, key = False, None
            elif key in (keys.REFRESH_TIME_INCREASE, keys.REFRESH_TIME_DECREASE):
                refresh_time = handlers.refresh_time(key, refresh_time)
            elif key is not None:
                query_mode = handlers.query_mode(key) or query_mode
                sort_key = handlers.sort_key_for(key, query_mode, is_local) or sort_key
            if not in_help:
                print(term.clear + term.home, end="")
                views.header(
                    term,
                    host,
                    dbinfo,
                    tps,
                    active_connections,
                    duration_mode,
                    refresh_time,
                    max_iops,
                    system_info,
                )
                views.query_mode(term, query_mode)
                views.columns_header(term, query_mode, flag, sort_key)

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
                    acts = activities.sorted(acts, key=sort_key, reverse=True)
                    views.processes_rows(
                        term,
                        acts,
                        is_local=is_local,
                        flag=flag,
                        query_mode=query_mode,
                        verbose_mode=verbose_mode,
                    )
                else:
                    print(f"{term.red}   UNHANDLED MODE{term.normal}{term.clear_eol}")

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
