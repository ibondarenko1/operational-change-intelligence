import json
from pathlib import Path
from typing import Any

from app.models.change import ChangeRequest


def _default_demo_assets_path() -> Path:
    current_file = Path(__file__).resolve()
    candidates = (
        current_file.parents[2] / "demo-data" / "demo_assets.json",
        current_file.parents[3] / "demo-data" / "demo_assets.json",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


DEFAULT_DEMO_ASSETS_PATH = _default_demo_assets_path()


def load_demo_asset_records(path: Path = DEFAULT_DEMO_ASSETS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as file:
        records = json.load(file)
    if not isinstance(records, list):
        raise ValueError("Demo assets file must contain a JSON array")
    return records


def get_demo_asset_context(
    change_request: ChangeRequest,
    path: Path = DEFAULT_DEMO_ASSETS_PATH,
) -> str:
    for record in load_demo_asset_records(path):
        if not _matches_change_request(record, change_request):
            continue
        return _asset_context_text(record)
    return ""


def _matches_change_request(record: dict[str, Any], change_request: ChangeRequest) -> bool:
    return (
        str(record.get("title", "")).lower() == change_request.title.lower()
        and str(record.get("environment", "")) == _enum_value(change_request.environment)
        and str(record.get("change_type", "")) == _enum_value(change_request.change_type)
    )


def _asset_context_text(record: dict[str, Any]) -> str:
    parts = [f"scenario={record.get('scenario_code', 'unknown')}"]
    for asset in record.get("assets", []):
        examples = asset.get("examples") or []
        example_text = f" examples: {', '.join(examples)}." if examples else ""
        parts.append(
            f"{asset.get('count', 0)} {asset.get('asset_type', 'assets')}: "
            f"{asset.get('description', '')}{example_text}"
        )
    return " ".join(parts)


def _enum_value(value: object) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)
