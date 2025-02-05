from pgactivity import cli


def test_parser() -> None:
    parser = cli.get_parser()
    ns = parser.parse_args(
        ["--no-db-size", "-w", "-p", "5433", "--no-pid", "--no-app-name"]
    )
    assert vars(ns) == {
        "profile": None,
        "blocksize": 4096,
        "rds": False,
        "output": None,
        "dbsize": False,
        "tempfiles": None,
        "walreceiver": None,
        "wrap_query": True,
        "durationmode": "1",
        "minduration": 0,
        "filters": [],
        "debug_file": None,
        "help": False,
        "connection_string": "",
        "host": None,
        "port": "5433",
        "username": None,
        "dbname": None,
        "pid": False,
        "database": None,
        "user": None,
        "client": None,
        "cpu": None,
        "mem": None,
        "read": None,
        "write": None,
        "time": None,
        "wait": None,
        "xmin": None,
        "appname": False,
        "header_show_instance": None,
        "header_show_system": None,
        "header_show_workers": None,
        "hide_queries_in_logs": False,
        "refresh": 2,
    }


def test_parser_flag_on() -> None:
    parser = cli.get_parser()
    ns = parser.parse_args(["--pid", "--no-app-name"])
    assert ns.pid is True
    assert ns.appname is False
    assert ns.wait is None
