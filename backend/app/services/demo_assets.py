import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.change import Asset, AssetDependency, ChangeAsset, ChangeRequest
from app.models.enums import AssetType, Criticality, DependencyType, Environment


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


def seed_demo_assets(
    db: Session,
    path: Path = DEFAULT_DEMO_ASSETS_PATH,
) -> dict[str, int]:
    records = load_demo_asset_records(path)
    inserted = 0
    updated = 0
    dependencies_inserted = 0
    dependencies_updated = 0
    total_assets = 0
    total_dependencies = 0

    for record in records:
        assets_by_name: dict[str, Asset] = {}
        for asset_record in record.get("assets", []):
            total_assets += 1
            asset_data = _asset_data(asset_record)
            existing = db.scalar(select(Asset).where(Asset.name == asset_data["name"]))
            if existing is None:
                existing = Asset(**asset_data)
                db.add(existing)
                inserted += 1
            else:
                for field, value in asset_data.items():
                    setattr(existing, field, value)
                updated += 1
            assets_by_name[existing.name] = existing

        db.flush()
        assets_by_name.update({asset.name: asset for asset in db.scalars(select(Asset)).all()})

        for dependency_record in record.get("dependencies", []):
            total_dependencies += 1
            dependency_data = _dependency_data(dependency_record, assets_by_name)
            existing_dependency = db.get(AssetDependency, dependency_data["id"])
            if existing_dependency is None:
                db.add(AssetDependency(**dependency_data))
                dependencies_inserted += 1
                continue

            for field, value in dependency_data.items():
                setattr(existing_dependency, field, value)
            dependencies_updated += 1

    db.commit()
    return {
        "assets_inserted": inserted,
        "assets_updated": updated,
        "assets_total": total_assets,
        "dependencies_inserted": dependencies_inserted,
        "dependencies_updated": dependencies_updated,
        "dependencies_total": total_dependencies,
    }


def attach_demo_assets_to_change(
    db: Session,
    change_request: ChangeRequest,
    path: Path = DEFAULT_DEMO_ASSETS_PATH,
) -> list[ChangeAsset]:
    records = load_demo_asset_records(path)
    matched_record = next(
        (record for record in records if _matches_change_request(record, change_request)),
        None,
    )
    if matched_record is None:
        return _load_change_assets(db, change_request)

    seed_demo_assets(db, path)

    assets_by_name = {asset.name: asset for asset in db.scalars(select(Asset)).all()}
    for relationship in matched_record.get("change_asset_relationships", []):
        asset = assets_by_name.get(str(relationship["asset"]))
        if asset is None:
            continue
        existing = db.get(
            ChangeAsset,
            (
                change_request.id,
                asset.id,
                str(relationship.get("relationship_type", "directly_affected")),
            ),
        )
        if existing is None:
            db.add(
                ChangeAsset(
                    change_request_id=change_request.id,
                    asset_id=asset.id,
                    relationship_type=str(relationship.get("relationship_type", "directly_affected")),
                    evidence=str(relationship.get("evidence", "Matched demo scenario scope.")),
                )
            )
        else:
            existing.evidence = str(relationship.get("evidence", existing.evidence))

    db.commit()
    return _load_change_assets(db, change_request)


def build_asset_context(change_assets: list[ChangeAsset]) -> str:
    parts: list[str] = []
    for change_asset in change_assets:
        asset = change_asset.asset
        metadata = asset.asset_metadata or {}
        count_text = ""
        if metadata.get("users_count"):
            count_text = f" users_count={metadata['users_count']}"
        parts.append(
            f"{asset.name} type={_enum_value(asset.asset_type)} criticality={_enum_value(asset.criticality)} "
            f"auth={asset.authentication_method or 'none'} legacy={asset.is_legacy} privileged={asset.is_privileged}"
            f"{count_text}. {asset.description}"
        )
    return " ".join(parts)


def _load_change_assets(db: Session, change_request: ChangeRequest) -> list[ChangeAsset]:
    statement = (
        select(ChangeAsset)
        .options(
            selectinload(ChangeAsset.asset).selectinload(Asset.outgoing_dependencies).selectinload(
                AssetDependency.target_asset
            ),
            selectinload(ChangeAsset.asset).selectinload(Asset.incoming_dependencies).selectinload(
                AssetDependency.source_asset
            ),
        )
        .where(ChangeAsset.change_request_id == change_request.id)
        .order_by(ChangeAsset.relationship_type.asc())
    )
    return list(db.scalars(statement).all())


def _matches_change_request(record: dict[str, Any], change_request: ChangeRequest) -> bool:
    return (
        str(record.get("title", "")).lower() == change_request.title.lower()
        and str(record.get("environment", "")) == _enum_value(change_request.environment)
        and str(record.get("change_type", "")) == _enum_value(change_request.change_type)
    )


def _asset_context_text(record: dict[str, Any]) -> str:
    parts = [f"scenario={record.get('scenario_code', 'unknown')}"]
    for asset in record.get("assets", []):
        examples = asset.get("examples") or [asset.get("name")]
        example_text = f" examples: {', '.join(examples)}." if examples else ""
        count = asset.get("count") or (asset.get("asset_metadata") or {}).get("users_count") or 1
        parts.append(
            f"{count} {asset.get('asset_type', 'assets')}: "
            f"{asset.get('description', '')}{example_text}"
        )
    return " ".join(parts)


def _enum_value(value: object) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _asset_data(asset_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": uuid.UUID(str(asset_record["id"])),
        "name": str(asset_record["name"]),
        "asset_type": AssetType(str(asset_record["asset_type"])),
        "environment": Environment(str(asset_record["environment"])),
        "description": str(asset_record["description"]),
        "business_service": asset_record.get("business_service"),
        "owner": asset_record.get("owner"),
        "criticality": Criticality(str(asset_record["criticality"])),
        "authentication_method": asset_record.get("authentication_method"),
        "is_legacy": bool(asset_record.get("is_legacy", False)),
        "is_privileged": bool(asset_record.get("is_privileged", False)),
        "asset_metadata": asset_record.get("asset_metadata") or {},
    }


def _dependency_data(
    dependency_record: dict[str, Any],
    assets_by_name: dict[str, Asset],
) -> dict[str, Any]:
    source = assets_by_name[str(dependency_record["source"])]
    target = assets_by_name[str(dependency_record["target"])]
    return {
        "id": uuid.UUID(str(dependency_record["id"])),
        "source_asset_id": source.id,
        "target_asset_id": target.id,
        "dependency_type": DependencyType(str(dependency_record["dependency_type"])),
        "description": str(dependency_record["description"]),
    }
