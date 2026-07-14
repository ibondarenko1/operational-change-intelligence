from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import get_engine, get_session_factory  # noqa: E402
from app.models.base import Base  # noqa: E402
import app.models  # noqa: F401, E402
from app.services.historical_changes import DEFAULT_DEMO_DATA_PATH, seed_historical_changes  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed synthetic historical Microsoft security change records.")
    parser.add_argument(
        "--data-file",
        type=Path,
        default=DEFAULT_DEMO_DATA_PATH,
        help="Path to historical_changes.json",
    )
    parser.add_argument(
        "--create-tables",
        action="store_true",
        help="Create tables before seeding. Useful for local SQLite verification.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = get_engine()

    if args.create_tables:
        Base.metadata.create_all(bind=engine)

    session_factory = get_session_factory()
    with session_factory() as session:
        result = seed_historical_changes(session, args.data_file)

    print(
        "Seeded historical changes: "
        f"inserted={result['inserted']} updated={result['updated']} total={result['total']}"
    )


if __name__ == "__main__":
    main()
