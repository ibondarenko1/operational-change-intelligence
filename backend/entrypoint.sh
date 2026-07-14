#!/bin/sh
set -eu

python -m alembic upgrade head

if [ "${DEMO_MODE:-false}" = "true" ]; then
  python - <<'PY'
from app.db.session import get_session_factory
from app.services.historical_changes import seed_historical_changes

session_factory = get_session_factory()
with session_factory() as session:
    result = seed_historical_changes(session)

print(
    "Seeded historical changes: "
    f"inserted={result['inserted']} updated={result['updated']} total={result['total']}"
)
PY
fi

exec "$@"
