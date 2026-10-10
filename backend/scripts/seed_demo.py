from pathlib import Path
import os
import sys
import argparse

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
from app.database import SessionLocal  # noqa: E402
from app.mvp.seed import seed  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset", action="store_true", help="Rebuild synthetic pilot data, discarding pilot demo events"
    )
    args = parser.parse_args()
    with SessionLocal() as db:
        seed(db, reset=args.reset)
    print("Synthetic scope-v1 pilot initialized.")
