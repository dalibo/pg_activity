from unittest.mock import MagicMock

import pytest

from pgactivity import cli, types, ui
from pgactivity.pg import OperationalError


@pytest.mark.parametrize("paused", [False, True])
def test_ui_settings_survive_reconnect(monkeypatch, paused):
    monkeypatch.setattr("sys.argv", ["pg_activity"])
    data = MagicMock()
    data.pg_is_local.return_value = False
    data.filters = types.Filters()
    data.pg_conn.info.port = "5432"
    data.pg_get_server_information.return_value.max_dbname_length = 8
    data.pg_get_activities.return_value = []
    data.pg_get_waiting.return_value = []
    reconnected = MagicMock(wraps=data)
    data.try_reconnect.return_value = reconnected
    monkeypatch.setattr(cli.data, "pg_connect", lambda *a, **kw: data)
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)
    term = MagicMock()
    term.clear = term.home = ""
    monkeypatch.setattr(cli, "Terminal", lambda: term)
    screens = []

    def screen(term, state, **kwargs):
        screens.append(state)
        if len(screens) == 1:
            state.refresh_time = 5
            state.query_mode = types.QueryMode.waiting
            state.wrap_query = True
            state.header.toggle_system()
            state.in_pause = paused
            state.start_interactive()
            raise OperationalError("connection lost")
        assert state.refresh_time == 5
        assert state.query_mode == types.QueryMode.waiting
        assert state.wrap_query is True
        assert state.in_pause is paused
        assert not state.interactive()
        assert state.header == screens[0].header
        raise KeyboardInterrupt

    monkeypatch.setattr(ui.views, "screen", screen)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    assert len(screens) == 2
    data.try_reconnect.assert_called_once()
    if paused:
        reconnected.pg_get_waiting.assert_not_called()
    else:
        reconnected.pg_get_waiting.assert_called_once()
