#!/bin/sh
set -eu

python -m alembic upgrade head

if [ "${DEMO_MODE:-false}" = "true" ]; then
  python - <<'PY'
from app.db.session import get_session_factory
from app.services.demo_assets import seed_demo_assets
from app.services.historical_changes import seed_historical_changes

session_factory = get_session_factory()
with session_factory() as session:
    result = seed_historical_changes(session)
    asset_result = seed_demo_assets(session)

print(
    "Seeded historical changes: "
    f"inserted={result['inserted']} updated={result['updated']} total={result['total']}"
)
print(
    "Seeded demo assets: "
    f"inserted={asset_result['assets_inserted']} "
    f"updated={asset_result['assets_updated']} "
    f"total={asset_result['assets_total']} "
    f"dependencies={asset_result['dependencies_total']}"
)
PY
fi

exec "$@"
