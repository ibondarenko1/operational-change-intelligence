import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.change import ChangeRequest, HistoricalChange
from app.services.change_requests import get_change_request
from app.services.demo_assets import get_demo_asset_context


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "before",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "no",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


@dataclass(frozen=True)
class SimilarHistoricalChange:
    historical_change_id: uuid.UUID
    title: str
    similarity_score: float
    matching_factors: list[str]
    outcome: str
    incident_occurred: bool
    root_cause: str | None
    downtime_minutes: int
    rollback_required: bool
    lessons_learned: str | None
    historical_failure_signal: bool
    historical_severity: str


class SimilarityService:
    weights = {
        "environment": 0.18,
        "change_type": 0.22,
        "title_keywords": 0.14,
        "description_keywords": 0.14,
        "affected_scope": 0.12,
        "object_types": 0.08,
        "authentication_methods": 0.08,
        "policy_type": 0.04,
    }

    def find_similar(
        self,
        change_request: ChangeRequest,
        historical_changes: list[HistoricalChange],
        limit: int = 5,
        asset_context: str = "",
    ) -> list[SimilarHistoricalChange]:
        limit = min(max(limit, 1), 20)
        results = [
            self.score_historical_change(change_request, historical_change, asset_context=asset_context)
            for historical_change in historical_changes
        ]
        results.sort(
            key=lambda result: (
                -result.similarity_score,
                str(result.historical_change_id),
            )
        )
        return results[:limit]

    def score_historical_change(
        self,
        change_request: ChangeRequest,
        historical_change: HistoricalChange,
        asset_context: str = "",
    ) -> SimilarHistoricalChange:
        score = 0.0
        matching_factors: list[str] = []
        change_text = self._change_text(change_request, asset_context=asset_context)
        historical_text = self._historical_text(historical_change)

        if self._value(change_request.environment) == self._value(historical_change.environment):
            score += self.weights["environment"]
            matching_factors.append(f"environment={self._value(change_request.environment)}")

        if self._value(change_request.change_type) == self._value(historical_change.change_type):
            score += self.weights["change_type"]
            matching_factors.append(f"change_type={self._value(change_request.change_type)}")

        title_score, title_matches = self._token_coverage(change_request.title, historical_change.title)
        if title_score:
            score += self.weights["title_keywords"] * title_score
            matching_factors.append(f"title_keywords={', '.join(title_matches)}")

        description_score, description_matches = self._token_coverage(
            change_request.description,
            historical_change.description,
        )
        if description_score:
            score += self.weights["description_keywords"] * description_score
            matching_factors.append(f"description_keywords={', '.join(description_matches)}")

        scope_score, scope_matches = self._token_coverage(change_request.affected_scope, historical_text)
        if scope_score:
            score += self.weights["affected_scope"] * scope_score
            matching_factors.append(f"affected_scope_keywords={', '.join(scope_matches)}")

        object_type_score, object_type_matches = self._set_overlap_score(
            self._extract_object_types(change_text),
            self._extract_object_types(historical_text),
        )
        if object_type_score:
            score += self.weights["object_types"] * object_type_score
            matching_factors.append(f"object_types={', '.join(object_type_matches)}")

        auth_score, auth_matches = self._set_overlap_score(
            self._extract_authentication_methods(change_text),
            self._extract_authentication_methods(historical_text),
        )
        if auth_score:
            score += self.weights["authentication_methods"] * auth_score
            matching_factors.append(f"authentication_methods={', '.join(auth_matches)}")

        policy_score, policy_matches = self._set_overlap_score(
            self._extract_policy_types(change_text),
            self._extract_policy_types(historical_text),
        )
        if policy_score:
            score += self.weights["policy_type"] * policy_score
            matching_factors.append(f"policy_type={', '.join(policy_matches)}")

        historical_failure_signal = self._historical_failure_signal(historical_change)

        return SimilarHistoricalChange(
            historical_change_id=historical_change.id,
            title=historical_change.title,
            similarity_score=round(min(1.0, score), 4),
            matching_factors=matching_factors,
            outcome=historical_change.outcome,
            incident_occurred=historical_change.incident_occurred,
            root_cause=historical_change.root_cause,
            downtime_minutes=historical_change.downtime_minutes,
            rollback_required=historical_change.rollback_required,
            lessons_learned=historical_change.lessons_learned,
            historical_failure_signal=historical_failure_signal,
            historical_severity=self._historical_severity(historical_change, historical_failure_signal),
        )

    def _token_coverage(self, query_text: str, candidate_text: str) -> tuple[float, list[str]]:
        query_tokens = self._tokens(query_text)
        if not query_tokens:
            return 0.0, []

        candidate_tokens = self._tokens(candidate_text)
        matches = sorted(query_tokens & candidate_tokens)
        if not matches:
            return 0.0, []
        return len(matches) / len(query_tokens), matches

    def _set_overlap_score(self, query_values: set[str], candidate_values: set[str]) -> tuple[float, list[str]]:
        if not query_values:
            return 0.0, []
        matches = sorted(query_values & candidate_values)
        if matches:
            return len(matches) / len(query_values), matches
        return 0.0, []

    def _change_text(self, change_request: ChangeRequest, asset_context: str = "") -> str:
        return " ".join(
            [
                change_request.title,
                change_request.description,
                change_request.affected_scope,
                change_request.rollback_plan,
                self._value(change_request.environment),
                self._value(change_request.change_type),
                asset_context,
            ]
        )

    def _historical_text(self, historical_change: HistoricalChange) -> str:
        return " ".join(
            value
            for value in (
                historical_change.title,
                historical_change.description,
                historical_change.lessons_learned,
                self._value(historical_change.environment),
                self._value(historical_change.change_type),
            )
            if value
        )

    def _extract_object_types(self, text: str) -> set[str]:
        lowered = text.lower()
        object_types: set[str] = set()
        indicators = {
            "contractor_accounts": ("contractor", "external account", "vendor account"),
            "service_account": ("service account", "automation", "workload identity", "daemon"),
            "break_glass_account": ("break-glass", "break glass", "emergency access"),
            "legacy_application": ("legacy application", "legacy business", "old client", "legacy portal"),
            "vpn": ("vpn", "remote access"),
            "policy": ("policy", "conditional access", "enforcement"),
            "privileged_account": ("privileged", "administrator", "admin", "global administrator"),
            "guest_account": ("guest", "external user"),
            "device_group": ("device", "compliance"),
        }
        for object_type, keywords in indicators.items():
            if any(keyword in lowered for keyword in keywords):
                object_types.add(object_type)
        return object_types

    def _extract_authentication_methods(self, text: str) -> set[str]:
        lowered = text.lower().replace("-", "_")
        methods: set[str] = set()
        indicators = {
            "mfa": ("mfa", "multifactor", "authenticator"),
            "basic_auth": ("basic auth", "basic_auth", "basic authentication"),
            "ews": ("ews", "exchange web services"),
            "smtp_auth": ("smtp auth", "smtp_auth"),
            "radius": ("radius",),
            "legacy_client": ("legacy client", "old client", "legacy_client"),
            "password": ("password",),
            "conditional_access": ("conditional access",),
        }
        for method, keywords in indicators.items():
            if any(keyword in lowered for keyword in keywords):
                methods.add(method)
        return methods

    def _extract_policy_types(self, text: str) -> set[str]:
        lowered = text.lower().replace("-", "_")
        policy_types: set[str] = set()
        indicators = {
            "mfa_rollout": ("mfa", "multifactor", "authenticator"),
            "conditional_access": ("conditional access", "ca policy"),
            "legacy_authentication_block": ("legacy authentication", "basic auth", "smtp auth", "imap", "pop"),
            "defender_policy": ("defender", "endpoint detection"),
            "device_compliance": ("device compliance", "managed devices", "unmanaged devices"),
            "password_policy": ("password policy", "password reset", "password expiration"),
        }
        for policy_type, keywords in indicators.items():
            if any(keyword in lowered for keyword in keywords):
                policy_types.add(policy_type)
        return policy_types

    def _historical_failure_signal(self, historical_change: HistoricalChange) -> bool:
        return (
            historical_change.outcome == "failed"
            or historical_change.incident_occurred
            or historical_change.rollback_required
        )

    def _historical_severity(self, historical_change: HistoricalChange, failure_signal: bool) -> str:
        if not failure_signal:
            return "low"
        if historical_change.downtime_minutes >= 240:
            return "critical"
        if historical_change.downtime_minutes >= 60 or historical_change.rollback_required:
            return "high"
        return "medium"

    def _tokens(self, text: str | None) -> set[str]:
        if not text:
            return set()

        tokens = set()
        for match in TOKEN_PATTERN.findall(text.lower()):
            if match in STOPWORDS or len(match) < 2:
                continue
            tokens.add(self._normalize_token(match))
        return tokens

    def _normalize_token(self, token: str) -> str:
        if token.endswith("ies") and len(token) > 4:
            return f"{token[:-3]}y"
        if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
            return token[:-1]
        return token

    def _value(self, value: object) -> str:
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)


def find_similar_changes(
    db: Session,
    change_request_id: uuid.UUID,
    limit: int = 5,
    similarity_service: SimilarityService | None = None,
) -> list[SimilarHistoricalChange]:
    change_request = get_change_request(db, change_request_id)
    historical_changes = list(db.scalars(select(HistoricalChange)).all())
    return (similarity_service or SimilarityService()).find_similar(
        change_request=change_request,
        historical_changes=historical_changes,
        limit=limit,
        asset_context=get_demo_asset_context(change_request),
    )
