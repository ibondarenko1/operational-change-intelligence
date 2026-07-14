from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.models.change import ChangeRequest, HistoricalChange
from app.services.similarity import SimilarHistoricalChange, SimilarityService


DEFAULT_RULES_PATH = Path(__file__).resolve().parents[1] / "rules" / "change_risk_rules.yaml"
FORMULA = "score = min(100, max(0, sum(min(sum(points by category), category_cap))))"


@dataclass(frozen=True)
class RiskFactorResult:
    code: str
    title: str
    description: str
    category: str
    category_cap: int
    points: int
    evidence: str


@dataclass(frozen=True)
class ChecklistItemResult:
    code: str
    title: str
    description: str
    priority: str
    status: str


@dataclass(frozen=True)
class RiskAssessmentResult:
    score: int
    raw_score: int
    capped_score: int
    category_scores: dict[str, dict[str, int]]
    level: str
    recommendation: str
    confidence: float
    formula: str
    formula_explanation: str
    risk_factors: list[RiskFactorResult]
    checklist_items: list[ChecklistItemResult]


class _MissingFormatValue(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "unknown"


class RiskEngine:
    def __init__(
        self,
        rules_path: Path = DEFAULT_RULES_PATH,
        similarity_service: SimilarityService | None = None,
    ) -> None:
        self.rules_path = rules_path
        self.rules = self._load_rules(rules_path)
        self.similarity_service = similarity_service or SimilarityService()

    def analyze(
        self,
        change_request: ChangeRequest,
        historical_changes: list[HistoricalChange] | None = None,
        asset_context: str | None = None,
        similar_changes: list[SimilarHistoricalChange] | None = None,
    ) -> RiskAssessmentResult:
        historical_changes = historical_changes or []
        asset_context = asset_context or ""
        factors: list[RiskFactorResult] = []
        checklist_items: list[ChecklistItemResult] = []
        matched_codes: set[str] = set()

        for rule in self.rules:
            if rule["code"] == "weak_rollback_validation" and "rollback_plan_missing" in matched_codes:
                continue
            matched, context, dynamic_points = self._evaluate_rule(
                rule,
                change_request,
                historical_changes,
                asset_context,
                similar_changes,
            )
            if not matched:
                continue

            points = dynamic_points if dynamic_points is not None else int(rule["points"])
            category = str(rule["category"])
            category_cap = int(rule["category_cap"])
            factors.append(
                RiskFactorResult(
                    code=rule["code"],
                    title=rule["title"],
                    description=rule["description"],
                    category=category,
                    category_cap=category_cap,
                    points=points,
                    evidence=str(rule["evidence_template"]).format_map(_MissingFormatValue(context)),
                )
            )
            checklist_items.extend(self._build_checklist_items(rule))
            matched_codes.add(rule["code"])

        raw_score = sum(factor.points for factor in factors)
        category_scores = self._category_scores(factors)
        capped_score = sum(category["capped"] for category in category_scores.values())
        score = min(100, max(0, capped_score))
        level = self._level_for_score(score)

        return RiskAssessmentResult(
            score=score,
            raw_score=raw_score,
            capped_score=capped_score,
            category_scores=category_scores,
            level=level,
            recommendation=self._recommendation_for_level(level),
            confidence=self._confidence_for_factors(factors, historical_changes),
            formula=FORMULA,
            formula_explanation=self._formula_explanation(category_scores),
            risk_factors=factors,
            checklist_items=checklist_items,
        )

    def _load_rules(self, rules_path: Path) -> list[dict[str, Any]]:
        with rules_path.open(encoding="utf-8") as file:
            payload = yaml.safe_load(file)

        rules = payload.get("rules") if isinstance(payload, dict) else None
        if not isinstance(rules, list) or not rules:
            raise ValueError("Risk rules YAML must contain a non-empty 'rules' list")
        return rules

    def _evaluate_rule(
        self,
        rule: dict[str, Any],
        change_request: ChangeRequest,
        historical_changes: list[HistoricalChange],
        asset_context: str,
        similar_changes: list[SimilarHistoricalChange] | None,
    ) -> tuple[bool, dict[str, Any], int | None]:
        conditions = rule.get("conditions", {})
        condition_type = conditions.get("type")

        if condition_type == "keyword_any":
            return self._evaluate_keyword_any(conditions, change_request, asset_context)
        if condition_type == "rollback_missing":
            return self._evaluate_rollback_missing(conditions, change_request)
        if condition_type == "rollback_weak_validation":
            return self._evaluate_rollback_weak_validation(conditions, change_request)
        if condition_type == "bool_equals":
            return self._evaluate_bool_equals(conditions, change_request)
        if condition_type == "similar_failures":
            return self._evaluate_similar_failures(conditions, change_request, historical_changes, asset_context, similar_changes)

        raise ValueError(f"Unsupported rule condition type: {condition_type}")

    def _evaluate_keyword_any(
        self,
        conditions: dict[str, Any],
        change_request: ChangeRequest,
        asset_context: str,
    ) -> tuple[bool, dict[str, Any], int | None]:
        fields = conditions.get("fields", [])
        keywords = conditions.get("keywords", [])
        haystack = " ".join(
            self._field_value(change_request, field, asset_context) for field in fields
        ).lower()

        matches = sorted({keyword for keyword in keywords if str(keyword).lower() in haystack})
        return bool(matches), {"matches": ", ".join(matches)}, None

    def _evaluate_rollback_missing(
        self,
        conditions: dict[str, Any],
        change_request: ChangeRequest,
    ) -> tuple[bool, dict[str, Any], int | None]:
        field = conditions.get("field", "rollback_plan")
        value = self._field_value(change_request, field).strip()
        normalized = value.lower()
        minimum_length = int(conditions.get("minimum_length", 1))
        empty_markers = {str(marker).lower() for marker in conditions.get("empty_markers", [])}

        missing = not value or len(value) < minimum_length or normalized in empty_markers
        summary = value if value else "<empty>"
        if len(summary) > 100:
            summary = f"{summary[:97]}..."
        return missing, {"rollback_plan_summary": summary}, None

    def _evaluate_rollback_weak_validation(
        self,
        conditions: dict[str, Any],
        change_request: ChangeRequest,
    ) -> tuple[bool, dict[str, Any], int | None]:
        field = conditions.get("field", "rollback_plan")
        value = self._field_value(change_request, field).strip()
        lowered = value.lower()
        validation_keywords = [str(keyword).lower() for keyword in conditions.get("validation_keywords", [])]
        minimum_length = int(conditions.get("minimum_length", 60))

        validation_matches = [keyword for keyword in validation_keywords if keyword in lowered]
        weak = len(value) < minimum_length or not validation_matches
        context = {
            "rollback_plan_summary": value if value else "<empty>",
            "validation_matches": ", ".join(validation_matches) if validation_matches else "none",
        }
        return weak, context, None

    def _evaluate_bool_equals(
        self,
        conditions: dict[str, Any],
        change_request: ChangeRequest,
    ) -> tuple[bool, dict[str, Any], int | None]:
        field = str(conditions["field"])
        expected = bool(conditions["value"])
        actual = bool(getattr(change_request, field))
        return actual is expected, {field: str(actual).lower()}, None

    def _evaluate_similar_failures(
        self,
        conditions: dict[str, Any],
        change_request: ChangeRequest,
        historical_changes: list[HistoricalChange],
        asset_context: str,
        similar_changes: list[SimilarHistoricalChange] | None,
    ) -> tuple[bool, dict[str, Any], int | None]:
        minimum_similarity = float(conditions.get("minimum_similarity", 0.35))
        per_failure_points = int(conditions.get("per_failure_points", 10))
        max_points = int(conditions.get("max_points", 20))
        if similar_changes is None:
            similar_changes = self.similarity_service.find_similar(
                change_request,
                historical_changes,
                limit=min(max(len(historical_changes), 1), 20),
                asset_context=asset_context,
            )
        failed_changes = [
            similar_change
            for similar_change in similar_changes
            if similar_change.similarity_score >= minimum_similarity
            and similar_change.historical_failure_signal
        ]
        if not failed_changes:
            return False, {}, None

        weighted_points = round(
            sum(similar_change.similarity_score * per_failure_points for similar_change in failed_changes)
        )
        points = min(max_points, max(1, weighted_points))
        examples = "; ".join(
            f"{similar_change.title} ({similar_change.similarity_score:.2f})"
            for similar_change in failed_changes[:3]
        )

        return True, {
            "failure_count": len(failed_changes),
            "points": points,
            "examples": examples,
        }, points

    def _field_value(self, obj: object, field: str, asset_context: str = "") -> str:
        if field == "asset_context":
            return asset_context
        value = getattr(obj, field)
        if hasattr(value, "value"):
            return str(value.value)
        return str(value or "")

    def _build_checklist_items(self, rule: dict[str, Any]) -> list[ChecklistItemResult]:
        return [
            ChecklistItemResult(
                code=item["code"],
                title=item["title"],
                description=item["description"],
                priority=item["priority"],
                status=item["status"],
            )
            for item in rule.get("checklist_items", [])
        ]

    def _category_scores(self, factors: list[RiskFactorResult]) -> dict[str, dict[str, int]]:
        scores: dict[str, dict[str, int]] = {}
        for factor in factors:
            category = scores.setdefault(
                factor.category,
                {
                    "raw": 0,
                    "capped": 0,
                    "cap": factor.category_cap,
                },
            )
            category["raw"] += factor.points
            category["cap"] = factor.category_cap

        for category in scores.values():
            category["capped"] = min(category["raw"], category["cap"])
        return scores

    def _formula_explanation(self, category_scores: dict[str, dict[str, int]]) -> str:
        if not category_scores:
            return "No rules matched; score is 0."
        parts = [
            f"{category}: raw={values['raw']}, capped={values['capped']}, cap={values['cap']}"
            for category, values in sorted(category_scores.items())
        ]
        return "Category caps applied before final 0-100 clamp. " + "; ".join(parts)

    def _level_for_score(self, score: int) -> str:
        if score <= 29:
            return "low"
        if score <= 49:
            return "medium"
        if score <= 69:
            return "high"
        return "critical"

    def _recommendation_for_level(self, level: str) -> str:
        recommendations = {
            "low": "proceed",
            "medium": "proceed_with_safeguards",
            "high": "pilot_first",
            "critical": "delay_and_investigate",
        }
        return recommendations[level]

    def _confidence_for_factors(
        self,
        factors: list[RiskFactorResult],
        historical_changes: list[HistoricalChange],
    ) -> float:
        confidence = 0.6 + min(0.25, len(factors) * 0.03)
        if historical_changes:
            confidence += 0.1
        return round(min(0.95, confidence), 2)
