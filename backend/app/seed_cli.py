import argparse
from datetime import date, datetime

from .database import SessionLocal
from .main import today
from .seed import seed


def _clock(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("clock must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("clock must include a timezone offset")
    return parsed


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Seed the synthetic Islamabad primary-care demo.")
    parser.add_argument("--day", type=date.fromisoformat, help="service day (YYYY-MM-DD); defaults to today")
    parser.add_argument("--clock", type=_clock, help="declared seed time as timezone-aware ISO-8601")
    parser.add_argument("--reset", action="store_true", help="rebuild only the versioned synthetic demo rows")
    parser.add_argument(
        "--disposable-demo", action="store_true",
        help="confirm the demo fixture is disposable; required together with --reset",
    )
    args = parser.parse_args(argv)
    if args.reset != args.disposable_demo:
        parser.error("--reset and --disposable-demo must be supplied together")
    return args


def main(argv=None, session_factory=SessionLocal):
    args = parse_args(argv)
    service_day = args.day or today()
    with session_factory() as session:
        seed(session, service_day, clock=args.clock, reset=args.reset)
    action = "reset" if args.reset else "checked"
    print(f"Synthetic demo {action}; unrelated data preserved.")


if __name__ == "__main__":
    main()
