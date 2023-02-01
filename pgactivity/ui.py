import time
from argparse import Namespace
from functools import partial
from typing import Dict, List, Optional, cast

import attr
from blessed import Terminal

from . import __version__, activities, handlers, keys, types, utils, views, widgets
from .data import Data


def main(
    term: Terminal,
    data: Data,
    host: types.Host,
    options: Namespace,
    *,
    render_header: bool = True,
    render_footer: bool = True,
    width: Optional[int] = None,
    wait_on_actions: Optional[float] = None,
) -> None:
    fs_blocksize = options.blocksize

    is_local = data.pg_is_local() and data.pg_is_local_access()

    skip_db_size = options.nodbsize
    server_information = data.pg_get_server_information(
        prev_server_info=None,
        using_rds=options.rds,
        skip_db_size=options.nodbsize,
        skip_tempfile=options.notempfiles,
        skip_walreceiver=options.nowalreceiver,
    )

    flag = types.Flag.from_options(is_local=is_local, **vars(options))
    ui = types.UI.make(
        flag=flag,
        refresh_time=options.refresh,
        min_duration=options.minduration,
        duration_mode=int(options.durationmode),
        wrap_query=options.wrap_query,
        max_db_length=min(max(server_information.max_dbname_length, 8), 16),
        filters=data.filters,
        show_instance_info_in_header=options.show_instance_info_in_header,
        show_worker_info_in_header=options.show_worker_info_in_header,
        show_system_info_in_header=options.show_system_info_in_header,
    )

    key, in_help = None, False
    sys_procs: Dict[int, types.SystemProcess] = {}
    pg_procs = types.SelectableProcesses([])
    activity_stats: types.ActivityStats

    msg_pile = utils.MessagePile(2)

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        while True:
            if key == keys.HELP:
                in_help = True
            elif in_help and key is not None:
                in_help, key = False, None
                print(term.clear + term.home, end="")
            elif key == keys.EXIT:
                break
            elif not ui.interactive() and key == keys.SPACE:
                ui.toggle_pause()
            elif options.nodbsize and key == keys.REFRESH_DB_SIZE:
                skip_db_size = False
            elif key is not None:
                if keys.is_process_next(key):
                    if pg_procs.focus_next():
                        ui.start_interactive()
                elif keys.is_process_prev(key):
                    if pg_procs.focus_prev():
                        ui.start_interactive()
                elif keys.is_process_nextpage(key):
                    if pg_procs.focus_next(term.height // 3):
                        ui.start_interactive()
                elif keys.is_process_prevpage(key):
                    if pg_procs.focus_prev(term.height // 3):
                        ui.start_interactive()
                elif keys.is_process_first(key):
                    if pg_procs.focus_first():
                        ui.start_interactive()
                elif keys.is_process_last(key):
                    if pg_procs.focus_last():
                        ui.start_interactive()
                elif key == keys.SPACE:
                    pg_procs.toggle_pin_focused()
                elif key.name == keys.CANCEL_SELECTION:
                    pg_procs.reset()
                    ui.end_interactive()
                elif keys.is_toggle_header_sys_info(key):
                    ui.toggle_system_info_in_header()
                elif keys.is_toggle_header_inst_info(key):
                    ui.toggle_instance_info_in_header()
                elif keys.is_toggle_header_worker_info(key):
                    ui.toggle_worker_info_in_header()
                elif pg_procs.selected and key in (
                    keys.PROCESS_CANCEL,
                    keys.PROCESS_KILL,
                ):
                    action, color = {
                        keys.PROCESS_CANCEL: ("cancel", "yellow"),
                        keys.PROCESS_KILL: ("terminate", "red"),
                    }[key]
                    action_formatter = getattr(term, color)
                    pids = pg_procs.selected
                    if len(pids) > 1:
                        ptitle = f"processes {', '.join((str(p) for p in pids))}"
                    else:
                        ptitle = f"process {pids[0]}"
                    with term.location(x=0, y=term.height // 3):
                        print(
                            widgets.boxed(
                                term,
                                f"Confirm {action_formatter(action)} action on {ptitle}? (y/n)",
                                border_color=color,
                                center=True,
                                width=width,
                            ),
                            end="",
                        )
                        confirm_key = term.inkey(timeout=None)
                    if confirm_key.lower() == "y":
                        if action == "cancel":
                            for pid in pids:
                                data.pg_cancel_backend(pid)
                            msg_pile.send(
                                action_formatter(f"{ptitle.capitalize()} cancelled")
                            )
                        elif action == "terminate":
                            for pid in pids:
                                data.pg_terminate_backend(pid)
                            msg_pile.send(
                                action_formatter(f"{ptitle.capitalize()} terminated")
                            )
                        pg_procs.reset()
                        ui.end_interactive()
                        if wait_on_actions:
                            # Used in tests.
                            time.sleep(wait_on_actions)
                else:
                    pg_procs.reset()
                    ui.end_interactive()
                    changes = {
                        "duration_mode": handlers.duration_mode(key, ui.duration_mode),
                        "wrap_query": handlers.wrap_query(key, ui.wrap_query),
                    }
                    if key in (keys.REFRESH_TIME_INCREASE, keys.REFRESH_TIME_DECREASE):
                        changes["refresh_time"] = handlers.refresh_time(
                            key, ui.refresh_time
                        )
                    query_mode = handlers.query_mode(key)
                    if query_mode is not None:
                        changes["query_mode"] = query_mode
                    else:
                        query_mode = ui.query_mode
                    sort_key = handlers.sort_key_for(key, query_mode, flag)
                    if sort_key is not None:
                        changes["sort_key"] = sort_key
                    ui.evolve(**changes)

            if in_help:
                # Only draw help screen once.
                if key is not None:
                    print(term.clear + term.home, end="")
                    views.help(
                        term,
                        __version__,
                        is_local,
                        lines_counter=views.line_counter(term.height),
                    )

            else:
                if not ui.in_pause and not ui.interactive():
                    if options.nodbsize and not skip_db_size:
                        skip_db_size = True

                    server_information = data.pg_get_server_information(
                        prev_server_info=server_information,
                        using_rds=options.rds,
                        skip_db_size=skip_db_size,
                        skip_tempfile=options.notempfiles,
                        skip_walreceiver=options.nowalreceiver,
                    )
                    memory, swap, load = activities.mem_swap_load()
                    system_info = types.SystemInfo.default(
                        memory=memory, swap=swap, load=load
                    )

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

                    activity_stats = (pg_procs, system_info) if is_local else pg_procs  # type: ignore[assignment]

                if options.output is not None:
                    custom_asdict = partial(attr.asdict, recurse=True)
                    with open(options.output, "a") as f:
                        utils.csv_write(f, map(custom_asdict, pg_procs.items))

                views.screen(
                    term,
                    ui,
                    host=host,
                    pg_version=data.pg_version,
                    server_information=server_information,
                    activity_stats=activity_stats,
                    message=msg_pile.get(),
                    render_header=render_header,
                    render_footer=render_footer,
                    width=width,
                )

                if ui.interactive():
                    if not pg_procs.pinned:
                        ui.tick_interactive()
                elif pg_procs.selected:
                    pg_procs.reset()

            key = term.inkey(timeout=ui.refresh_time) or None
