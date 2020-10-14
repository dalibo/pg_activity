import optparse
import os
import socket
from typing import Dict, Optional

import attr
from blessed import Terminal

from . import __version__, activities, handlers, keys, types, utils, views


def main(
    options: optparse.Values,
    *,
    term: Optional[Terminal] = None,
    render_footer: bool = True,
) -> None:
    data = utils.pg_connect(
        options,
        password=os.environ.get("PGPASSWORD"),
        service=os.environ.get("PGSERVICE"),
        min_duration=options.minduration,
    )

    hostname = socket.gethostname()
    fs_blocksize = options.blocksize

    host = types.Host(
        data.pg_version,
        hostname,
        options.username,
        options.host,
        options.port,
        options.dbname,
    )

    is_local = data.pg_is_local() and data.pg_is_local_access()

    skip_sizes = options.nodbsize
    pg_db_info = data.pg_get_db_info(
        None, using_rds=options.rds, skip_sizes=options.nodbsize
    )
    # TODO: use max_db_length to set template_h length of database column, see
    # set_max_db_length() method of old UI class.
    # max_db_length = min(max(pg_db_info["max_length"], 8), 16)
    # database_template_h = f"-{max_db_length}s "

    ui = types.UI(
        min_duration=options.minduration,
        flag=types.Flag.from_options(is_local=is_local, **vars(options)),
        duration_mode=int(options.durationmode),
        verbose_mode=int(options.verbosemode),
    )

    if term is None:
        # Used in tests.
        term = Terminal()
    key, in_help = None, False
    sys_procs: Dict[int, types.SystemProcess] = {}
    pg_procs: types.ProcessSet
    activity_stats: types.ActivityStats

    with term.fullscreen(), term.cbreak():
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
            memory, swap, load = activities.mem_swap_load()
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
                ui.in_pause = not ui.in_pause
            elif options.nodbsize and key == keys.REFRESH_DB_SIZE:
                skip_sizes = False
            elif key in (keys.REFRESH_TIME_INCREASE, keys.REFRESH_TIME_DECREASE):
                ui.refresh_time = handlers.refresh_time(key, ui.refresh_time)
            elif key is not None:
                ui.query_mode = handlers.query_mode(key) or ui.query_mode
                ui.sort_key = (
                    handlers.sort_key_for(key, ui.query_mode, is_local) or ui.sort_key
                )
                ui.duration_mode = handlers.duration_mode(key, ui.duration_mode)
                ui.verbose_mode = handlers.verbose_mode(key, ui.verbose_mode)
            if not in_help:
                if not ui.in_pause:
                    if is_local:
                        memory, swap, load = activities.mem_swap_load()
                        system_info = attr.evolve(
                            system_info,
                            memory=memory,
                            swap=swap,
                            load=load,
                        )

                    if ui.query_mode == types.QueryMode.activities:
                        pg_procs = data.pg_get_activities(ui.duration_mode)
                        if is_local:
                            # TODO: Use this logic in waiting and blocking cases.
                            (
                                io_read,
                                io_write,
                                pg_procs,
                            ) = activities.update_processes_local2(
                                pg_procs, sys_procs, fs_blocksize
                            )
                            system_info = attr.evolve(
                                system_info,
                                io_read=io_read,
                                io_write=io_write,
                                max_iops=activities.update_max_iops(
                                    system_info.max_iops,
                                    io_read.count,
                                    io_write.count,
                                ),
                            )
                            activity_stats = pg_procs, system_info
                        else:
                            activity_stats = pg_procs

                    else:
                        if ui.query_mode == types.QueryMode.blocking:
                            pg_procs = data.pg_get_blocking(ui.duration_mode)
                        elif ui.query_mode == types.QueryMode.waiting:
                            pg_procs = data.pg_get_waiting(ui.duration_mode)
                        else:
                            assert False  # help type checking

                        if is_local:
                            activity_stats = pg_procs, system_info
                        else:
                            activity_stats = pg_procs

                if options.output is not None:
                    with open(options.output, "a") as f:
                        utils.csv_write(f, map(attr.asdict, pg_procs))

                views.screen(
                    term,
                    ui,
                    host=host,
                    dbinfo=dbinfo,
                    tps=tps,
                    active_connections=active_connections,
                    activity_stats=activity_stats,
                    render_footer=render_footer,
                )

            key = term.inkey(timeout=ui.refresh_time) or None
