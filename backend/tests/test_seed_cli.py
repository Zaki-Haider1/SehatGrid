from datetime import date, datetime, timedelta, timezone

import pytest

from app import seed_cli
from app.seed_cli import parse_args


def test_seed_cli_accepts_declared_day_clock_and_explicit_disposable_reset():
    args = parse_args([
        "--day", "2026-10-10", "--clock", "2026-10-10T09:00:00+05:00",
        "--reset", "--disposable-demo",
    ])
    assert args.day == date(2026, 10, 10)
    assert args.clock == datetime(2026, 10, 10, 9, 0, tzinfo=timezone(timedelta(hours=5)))
    assert args.reset and args.disposable_demo


@pytest.mark.parametrize("arguments", [["--reset"], ["--disposable-demo"]])
def test_seed_cli_requires_explicit_disposable_demo_confirmation(arguments):
    with pytest.raises(SystemExit) as exit_info:
        parse_args(arguments)
    assert exit_info.value.code == 2


def test_seed_cli_requires_timezone_for_clock():
    with pytest.raises(SystemExit) as exit_info:
        parse_args(["--clock", "2026-10-10T09:00:00"])
    assert exit_info.value.code == 2


def test_seed_cli_passes_explicit_inputs_to_seed(monkeypatch):
    calls = []

    class SessionContext:
        def __enter__(self):
            return object()

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(seed_cli, "seed", lambda session, day, **kwargs: calls.append((day, kwargs)))
    monkeypatch.setattr(seed_cli, "today", lambda: date(2000, 1, 1))
    seed_cli.main([
        "--day", "2026-10-10", "--clock", "2026-10-10T09:00:00Z",
        "--reset", "--disposable-demo",
    ], session_factory=SessionContext)
    assert calls == [(date(2026, 10, 10), {
        "clock": datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc), "reset": True,
    })]
