from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.change import Asset, AssetDependency, ChangeAsset, ChangeRequest


DEFAULT_FAILURE_MODE_RULES_PATH = Path(__file__).resolve().parents[1] / "rules" / "failure_mode_rules.yaml"


@dataclass(frozen=True)
class ImpactAnalysisResult:
    directly_affected_assets: list[dict[str, Any]]
    dependent_assets: list[dict[str, Any]]
    affected_business_services: list[dict[str, Any]]
    impact_paths: list[dict[str, Any]]
    predicted_failure_modes: list[dict[str, Any]]
    blast_radius: dict[str, int]
    missing_context: list[str]


class ImpactAnalysisService:
    def __init__(self, rules_path: Path = DEFAULT_FAILURE_MODE_RULES_PATH) -> None:
        self.rules_path = rules_path
        self.rules = self._load_rules(rules_path)

    def analyze(
        self,
        db: Session,
        change_request: ChangeRequest,
        change_assets: list[ChangeAsset],
    ) -> ImpactAnalysisResult:
        direct_change_assets = [
            change_asset
            for change_asset in change_assets
            if change_asset.relationship_type == "directly_affected"
        ]
        direct_assets = [change_asset.asset for change_asset in direct_change_assets]
        dependencies = self._load_dependencies(db)
        dependencies_by_source = self._dependencies_by_source(dependencies)
        dependencies_by_target = self._dependencies_by_target(dependencies)
        reachable_assets = self._reachable_assets(direct_assets, dependencies_by_source)
        dependent_assets = [
            asset
            for asset in reachable_assets
            if asset.id not in {direct_asset.id for direct_asset in direct_assets}
            and self._value(asset.asset_type) != "business_service"
        ]
        impact_paths = self._build_impact_paths(change_request, direct_assets, dependencies_by_source)
        affected_business_services = self._affected_business_services(impact_paths, reachable_assets)
        predicted_failure_modes = self._predict_failure_modes(
            change_request,
            direct_assets + dependent_assets,
            dependencies_by_source,
            dependencies_by_target,
        )
        direct_payloads = [
            self._asset_payload(change_asset.asset, relationship_type=change_asset.relationship_type, evidence=change_asset.evidence)
            for change_asset in direct_change_assets
        ]
        dependent_payloads = [self._asset_payload(asset) for asset in dependent_assets]

        return ImpactAnalysisResult(
            directly_affected_assets=direct_payloads,
            dependent_assets=dependent_payloads,
            affected_business_services=affected_business_services,
            impact_paths=impact_paths,
            predicted_failure_modes=predicted_failure_modes,
            blast_radius=self._blast_radius(direct_assets, dependent_assets, affected_business_services),
            missing_context=self._missing_context(change_request, direct_assets + dependent_assets, dependencies_by_source),
        )

    def _load_rules(self, rules_path: Path) -> list[dict[str, Any]]:
        with rules_path.open(encoding="utf-8") as file:
            payload = yaml.safe_load(file)
        rules = payload.get("rules") if isinstance(payload, dict) else None
        if not isinstance(rules, list) or not rules:
            raise ValueError("Failure mode rules YAML must contain a non-empty 'rules' list")
        return rules

    def _load_dependencies(self, db: Session) -> list[AssetDependency]:
        statement = select(AssetDependency).options(
            selectinload(AssetDependency.source_asset),
            selectinload(AssetDependency.target_asset),
        )
        return list(db.scalars(statement).all())

    def _dependencies_by_source(
        self,
        dependencies: list[AssetDependency],
    ) -> dict[Any, list[AssetDependency]]:
        grouped: dict[Any, list[AssetDependency]] = {}
        for dependency in dependencies:
            grouped.setdefault(dependency.source_asset_id, []).append(dependency)
        return grouped

    def _dependencies_by_target(
        self,
        dependencies: list[AssetDependency],
    ) -> dict[Any, list[AssetDependency]]:
        grouped: dict[Any, list[AssetDependency]] = {}
        for dependency in dependencies:
            grouped.setdefault(dependency.target_asset_id, []).append(dependency)
        return grouped

    def _reachable_assets(
        self,
        direct_assets: list[Asset],
        dependencies_by_source: dict[Any, list[AssetDependency]],
        max_depth: int = 4,
    ) -> list[Asset]:
        seen = {asset.id for asset in direct_assets}
        ordered = list(direct_assets)
        frontier = [(asset, 0) for asset in direct_assets]

        while frontier:
            asset, depth = frontier.pop(0)
            if depth >= max_depth:
                continue
            for dependency in dependencies_by_source.get(asset.id, []):
                target = dependency.target_asset
                if target.id in seen:
                    continue
                seen.add(target.id)
                ordered.append(target)
                frontier.append((target, depth + 1))
        return ordered

    def _build_impact_paths(
        self,
        change_request: ChangeRequest,
        direct_assets: list[Asset],
        dependencies_by_source: dict[Any, list[AssetDependency]],
    ) -> list[dict[str, Any]]:
        paths: list[dict[str, Any]] = []
        change_label = self._value(change_request.change_type).replace("_", " ")

        for direct_asset in direct_assets:
            self._walk_paths(
                paths=paths,
                change_label=change_label,
                current_asset=direct_asset,
                dependencies_by_source=dependencies_by_source,
                path=[change_label, direct_asset.name],
                dependency_types=[],
                evidence=[],
                seen={direct_asset.id},
                depth=0,
            )

        unique: dict[str, dict[str, Any]] = {}
        for path in paths:
            key = "->".join(path["path"])
            unique.setdefault(key, path)
        return list(unique.values())[:12]

    def _walk_paths(
        self,
        paths: list[dict[str, Any]],
        change_label: str,
        current_asset: Asset,
        dependencies_by_source: dict[Any, list[AssetDependency]],
        path: list[str],
        dependency_types: list[str],
        evidence: list[str],
        seen: set[Any],
        depth: int,
    ) -> None:
        if depth > 4:
            return

        if self._value(current_asset.asset_type) == "business_service" and len(path) > 2:
            paths.append(
                {
                    "change": change_label,
                    "path": path,
                    "dependency_types": dependency_types,
                    "business_service": current_asset.name,
                    "evidence": "; ".join(evidence),
                }
            )
            return

        for dependency in dependencies_by_source.get(current_asset.id, []):
            target = dependency.target_asset
            if target.id in seen:
                continue
            self._walk_paths(
                paths=paths,
                change_label=change_label,
                current_asset=target,
                dependencies_by_source=dependencies_by_source,
                path=[*path, target.name],
                dependency_types=[*dependency_types, self._value(dependency.dependency_type)],
                evidence=[
                    *evidence,
                    f"{current_asset.name} {self._value(dependency.dependency_type)} {target.name}",
                ],
                seen={*seen, target.id},
                depth=depth + 1,
            )

    def _affected_business_services(
        self,
        impact_paths: list[dict[str, Any]],
        reachable_assets: list[Asset],
    ) -> list[dict[str, Any]]:
        by_name: dict[str, dict[str, Any]] = {}
        for asset in reachable_assets:
            if self._value(asset.asset_type) == "business_service":
                by_name[asset.name] = self._asset_payload(asset)
        for path in impact_paths:
            service_name = str(path["business_service"])
            by_name.setdefault(
                service_name,
                {
                    "name": service_name,
                    "asset_type": "business_service",
                    "criticality": "unknown",
                    "evidence": path["evidence"],
                },
            )
        return sorted(by_name.values(), key=lambda item: item["name"])

    def _predict_failure_modes(
        self,
        change_request: ChangeRequest,
        assets: list[Asset],
        dependencies_by_source: dict[Any, list[AssetDependency]],
        dependencies_by_target: dict[Any, list[AssetDependency]],
    ) -> list[dict[str, Any]]:
        modes: list[dict[str, Any]] = []
        change_type = self._value(change_request.change_type)

        for rule in self.rules:
            if change_type not in {str(item) for item in rule.get("change_types", [])}:
                continue
            for asset in assets:
                if not self._asset_matches(asset, rule.get("asset_conditions", {}), dependencies_by_source):
                    continue
                if not self._dependency_matches(
                    change_request,
                    asset,
                    rule.get("dependency_conditions", {}),
                    dependencies_by_source,
                    dependencies_by_target,
                ):
                    continue
                modes.append(self._failure_mode_payload(rule, asset, dependencies_by_source, dependencies_by_target))

        unique: dict[tuple[str, str], dict[str, Any]] = {}
        for mode in modes:
            unique.setdefault((mode["code"], mode["affected_asset"]), mode)
        return list(unique.values())

    def _asset_matches(
        self,
        asset: Asset,
        conditions: dict[str, Any],
        dependencies_by_source: dict[Any, list[AssetDependency]],
    ) -> bool:
        asset_type = self._value(asset.asset_type)
        if conditions.get("asset_type") and asset_type != conditions["asset_type"]:
            return False
        if conditions.get("asset_type_any") and asset_type not in conditions["asset_type_any"]:
            return False
        if "is_legacy" in conditions and asset.is_legacy is not bool(conditions["is_legacy"]):
            return False
        if conditions.get("criticality_any") and self._value(asset.criticality) not in conditions["criticality_any"]:
            return False
        if conditions.get("authentication_method_any") and not self._auth_matches(
            asset.authentication_method,
            conditions["authentication_method_any"],
        ):
            return False
        if conditions.get("requires_exclusion") and self._has_confirmed_exclusion(asset, dependencies_by_source):
            return False
        return True

    def _dependency_matches(
        self,
        change_request: ChangeRequest,
        asset: Asset,
        conditions: dict[str, Any],
        dependencies_by_source: dict[Any, list[AssetDependency]],
        dependencies_by_target: dict[Any, list[AssetDependency]],
    ) -> bool:
        if not conditions:
            return True

        change_text = " ".join(
            [change_request.title, change_request.description, change_request.affected_scope]
        ).lower()
        if conditions.get("change_text_any") and not any(
            str(keyword).lower() in change_text for keyword in conditions["change_text_any"]
        ):
            return False

        if conditions.get("has_dependency_type"):
            dependency_types = {
                self._value(dependency.dependency_type)
                for dependency in [
                    *dependencies_by_source.get(asset.id, []),
                    *dependencies_by_target.get(asset.id, []),
                ]
            }
            if not dependency_types & {str(item) for item in conditions["has_dependency_type"]}:
                return False

        if conditions.get("supports_business_service") and not self._business_services_for_asset(
            asset,
            dependencies_by_source,
        ):
            return False

        return True

    def _failure_mode_payload(
        self,
        rule: dict[str, Any],
        asset: Asset,
        dependencies_by_source: dict[Any, list[AssetDependency]],
        dependencies_by_target: dict[Any, list[AssetDependency]],
    ) -> dict[str, Any]:
        business_services = self._business_services_for_asset(asset, dependencies_by_source)
        related_dependencies = [
            *dependencies_by_source.get(asset.id, []),
            *dependencies_by_target.get(asset.id, []),
        ]
        dependency_evidence = "; ".join(
            f"{dependency.source_asset.name} {self._value(dependency.dependency_type)} {dependency.target_asset.name}"
            for dependency in related_dependencies[:4]
        )
        evidence_parts = [
            f"{asset.name}: type={self._value(asset.asset_type)}, auth={asset.authentication_method or 'none'}, "
            f"legacy={asset.is_legacy}, criticality={self._value(asset.criticality)}"
        ]
        if dependency_evidence:
            evidence_parts.append(dependency_evidence)
        return {
            "code": rule["code"],
            "failure_mode": rule["failure_mode"],
            "affected_asset": asset.name,
            "asset_type": self._value(asset.asset_type),
            "business_service": ", ".join(business_services) if business_services else asset.business_service,
            "business_impact": rule["business_impact"],
            "evidence": " | ".join(evidence_parts),
            "recommended_actions": list(rule.get("recommended_actions", [])),
        }

    def _business_services_for_asset(
        self,
        asset: Asset,
        dependencies_by_source: dict[Any, list[AssetDependency]],
    ) -> list[str]:
        services = set()
        if asset.business_service:
            services.add(asset.business_service)
        for dependency in dependencies_by_source.get(asset.id, []):
            if (
                self._value(dependency.dependency_type) == "supports"
                and self._value(dependency.target_asset.asset_type) == "business_service"
            ):
                services.add(dependency.target_asset.name)
        return sorted(services)

    def _blast_radius(
        self,
        direct_assets: list[Asset],
        dependent_assets: list[Asset],
        affected_business_services: list[dict[str, Any]],
    ) -> dict[str, int]:
        scoped_assets = self._unique_assets([*direct_assets, *dependent_assets])
        return {
            "users_count": sum(int((asset.asset_metadata or {}).get("users_count", 0)) for asset in direct_assets),
            "applications_count": sum(1 for asset in scoped_assets if self._value(asset.asset_type) == "application"),
            "service_accounts_count": sum(
                1 for asset in scoped_assets if self._value(asset.asset_type) == "service_account"
            ),
            "business_services_count": len(affected_business_services),
            "critical_assets_count": sum(1 for asset in scoped_assets if self._value(asset.criticality) == "critical"),
        }

    def _missing_context(
        self,
        change_request: ChangeRequest,
        assets: list[Asset],
        dependencies_by_source: dict[Any, list[AssetDependency]],
    ) -> list[str]:
        missing: list[str] = []
        for asset in self._unique_assets(assets):
            if not asset.owner:
                missing.append(f"No owner found for {asset.name}.")
            if self._value(asset.asset_type) == "break_glass_account" and not self._has_confirmed_exclusion(
                asset,
                dependencies_by_source,
            ):
                missing.append(f"No confirmed Conditional Access exclusion for break-glass account {asset.name}.")

        rollback_plan = change_request.rollback_plan.lower()
        validation_keywords = ("tested", "validated", "verified", "confirm", "monitor")
        if not any(keyword in rollback_plan for keyword in validation_keywords):
            missing.append("No tested rollback evidence attached.")

        return sorted(set(missing))

    def _asset_payload(
        self,
        asset: Asset,
        relationship_type: str | None = None,
        evidence: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "id": str(asset.id),
            "name": asset.name,
            "asset_type": self._value(asset.asset_type),
            "environment": self._value(asset.environment),
            "description": asset.description,
            "business_service": asset.business_service,
            "owner": asset.owner,
            "criticality": self._value(asset.criticality),
            "authentication_method": asset.authentication_method,
            "is_legacy": asset.is_legacy,
            "is_privileged": asset.is_privileged,
            "asset_metadata": asset.asset_metadata or {},
        }
        if relationship_type is not None:
            payload["relationship_type"] = relationship_type
        if evidence is not None:
            payload["evidence"] = evidence
        return payload

    def _auth_matches(self, authentication_method: str | None, expected_methods: list[str]) -> bool:
        if not authentication_method:
            return False
        normalized = authentication_method.lower().replace("-", "_")
        return any(str(method).lower().replace("-", "_") in normalized for method in expected_methods)

    def _has_confirmed_exclusion(
        self,
        asset: Asset,
        dependencies_by_source: dict[Any, list[AssetDependency]],
    ) -> bool:
        for dependency in dependencies_by_source.get(asset.id, []):
            if self._value(dependency.dependency_type) != "protected_by":
                continue
            target_text = f"{dependency.target_asset.name} {dependency.target_asset.description}".lower()
            if "exclusion" in target_text:
                return True
        return False

    def _unique_assets(self, assets: list[Asset]) -> list[Asset]:
        unique: dict[Any, Asset] = {}
        for asset in assets:
            unique.setdefault(asset.id, asset)
        return list(unique.values())

    def _value(self, value: object) -> str:
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)
