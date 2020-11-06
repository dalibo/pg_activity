import optparse
import os
import socket
from typing import Dict, List, Optional, cast

import attr
from blessed import Terminal

from . import __version__, activities, handlers, keys, types, utils, views, widgets
from .data import pg_connect


def main(
    options: optparse.Values,
    *,
    term: Optional[Terminal] = None,
    render_header: bool = True,
    render_footer: bool = True,
) -> None:
    data = pg_connect(
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

    ui = types.UI.make(
        flag=types.Flag.from_options(is_local=is_local, **vars(options)),
        min_duration=options.minduration,
        duration_mode=int(options.durationmode),
        verbose_mode=int(options.verbosemode),
        max_db_length=min(max(int(pg_db_info["max_length"]), 8), 16),
    )

    if term is None:
        # Used in tests.
        term = Terminal()
    key, in_help, wait_for = None, False, None
    sys_procs: Dict[int, types.SystemProcess] = {}
    pg_procs = types.SelectableProcesses([])
    activity_stats: types.ActivityStats

    msg_pile = utils.MessagePile(2)

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
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
                ui = ui.toggle_pause()
            elif options.nodbsize and key == keys.REFRESH_DB_SIZE:
                skip_sizes = False
            elif key in (keys.REFRESH_TIME_INCREASE, keys.REFRESH_TIME_DECREASE):
                ui = ui.evolve(refresh_time=handlers.refresh_time(key, ui.refresh_time))
            elif key is not None:
                if keys.is_process_next(key):
                    pg_procs.select_next()
                    wait_for = 3
                elif keys.is_process_prev(key):
                    pg_procs.select_prev()
                    wait_for = 3
                elif key.name == keys.CANCEL_SELECTION:
                    pg_procs.selected = None
                    wait_for = None
                elif pg_procs.selected and key in (
                    keys.PROCESS_CANCEL,
                    keys.PROCESS_KILL,
                ):
                    action, color = {
                        keys.PROCESS_CANCEL: ("cancel", "orange"),
                        keys.PROCESS_KILL: ("terminate", "red"),
                    }[key]
                    action_formatter = term.formatter(color)
                    pid = pg_procs.selected
                    with term.location(x=0, y=term.height // 3):
                        print(
                            widgets.boxed(
                                term,
                                f"Confirm {action_formatter(action)} action on process {pid}? (y/n)",
                                border_color=color,
                                center=True,
                            ),
                            end="",
                        )
                        confirm_key = term.inkey(timeout=None)
                    if confirm_key.lower() == "y":
                        if action == "cancel":
                            data.pg_cancel_backend(pid)
                            msg_pile.send(action_formatter(f"Process {pid} cancelled"))
                        elif action == "terminate":
                            data.pg_terminate_backend(pid)
                            msg_pile.send(action_formatter(f"Process {pid} terminated"))
                        pg_procs.selected = None
                        wait_for = None
                else:
                    pg_procs.selected = None
                    wait_for = None
                    changes = {
                        "duration_mode": handlers.duration_mode(key, ui.duration_mode),
                        "verbose_mode": handlers.verbose_mode(key, ui.verbose_mode),
                    }
                    query_mode = handlers.query_mode(key)
                    if query_mode is not None:
                        changes["query_mode"] = query_mode
                    else:
                        query_mode = ui.query_mode
                    sort_key = handlers.sort_key_for(key, query_mode, is_local)
                    if sort_key is not None:
                        changes["sort_key"] = sort_key
                    ui = ui.evolve(**changes)
            if not in_help:
                if not ui.in_pause and wait_for is None:
                    if is_local:
                        memory, swap, load = activities.mem_swap_load()
                        system_info = attr.evolve(
                            system_info,
                            memory=memory,
                            swap=swap,
                            load=load,
                        )

                    if ui.query_mode == types.QueryMode.activities:
                        pg_procs.set_items(data.pg_get_activities(ui.duration_mode))
                        if is_local:
                            # TODO: Use this logic in waiting and blocking cases.
                            local_pg_procs, io_read, io_write = activities.ps_complete(
                                cast(List[types.RunningProcess], pg_procs.items),
                                sys_procs,
                                fs_blocksize,
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
                            pg_procs.set_items(local_pg_procs)

                    else:
                        if ui.query_mode == types.QueryMode.blocking:
                            pg_procs.set_items(data.pg_get_blocking(ui.duration_mode))
                        elif ui.query_mode == types.QueryMode.waiting:
                            pg_procs.set_items(data.pg_get_waiting(ui.duration_mode))
                        else:
                            assert False  # help type checking

                    activity_stats = (pg_procs, system_info) if is_local else pg_procs  # type: ignore

                if options.output is not None:
                    with open(options.output, "a") as f:
                        utils.csv_write(f, map(attr.asdict, pg_procs.items))

                views.screen(
                    term,
                    ui,
                    host=host,
                    dbinfo=dbinfo,
                    tps=tps,
                    active_connections=active_connections,
                    activity_stats=activity_stats,
                    message=msg_pile.get(),
                    render_header=render_header,
                    render_footer=render_footer,
                )

                if wait_for is not None:
                    wait_for -= 1
                    if wait_for == 0:
                        wait_for = None

            key = term.inkey(timeout=ui.refresh_time) or None
