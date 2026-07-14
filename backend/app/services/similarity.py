import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.change import ChangeRequest, HistoricalChange
from app.services.change_requests import get_change_request


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
    lessons_learned: str | None


class SimilarityService:
    weights = {
        "environment": 0.20,
        "change_type": 0.25,
        "title_keywords": 0.15,
        "description_keywords": 0.15,
        "affected_scope": 0.10,
        "incident": 0.05,
        "root_cause": 0.05,
        "rollback_required": 0.05,
    }

    def find_similar(
        self,
        change_request: ChangeRequest,
        historical_changes: list[HistoricalChange],
        limit: int = 5,
    ) -> list[SimilarHistoricalChange]:
        limit = min(max(limit, 1), 20)
        results = [
            self.score_historical_change(change_request, historical_change)
            for historical_change in historical_changes
        ]
        results.sort(
            key=lambda result: (
                -result.similarity_score,
                result.outcome != "failed",
                not result.incident_occurred,
                str(result.historical_change_id),
            )
        )
        return results[:limit]

    def score_historical_change(
        self,
        change_request: ChangeRequest,
        historical_change: HistoricalChange,
    ) -> SimilarHistoricalChange:
        score = 0.0
        matching_factors: list[str] = []

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

        historical_scope_text = " ".join(
            value
            for value in (
                historical_change.title,
                historical_change.description,
                historical_change.lessons_learned,
            )
            if value
        )
        scope_score, scope_matches = self._token_coverage(change_request.affected_scope, historical_scope_text)
        if scope_score:
            score += self.weights["affected_scope"] * scope_score
            matching_factors.append(f"affected_scope_keywords={', '.join(scope_matches)}")

        if historical_change.incident_occurred:
            score += self.weights["incident"]
            matching_factors.append("historical_incident=true")

        if historical_change.root_cause:
            root_cause_score, root_cause_matches = self._root_cause_score(change_request, historical_change.root_cause)
            score += self.weights["root_cause"] * root_cause_score
            if root_cause_matches:
                matching_factors.append(
                    f"root_cause={historical_change.root_cause}; matched_keywords={', '.join(root_cause_matches)}"
                )
            else:
                matching_factors.append(f"root_cause={historical_change.root_cause}")

        if historical_change.rollback_required:
            score += self.weights["rollback_required"]
            matching_factors.append("rollback_required=true")

        return SimilarHistoricalChange(
            historical_change_id=historical_change.id,
            title=historical_change.title,
            similarity_score=round(min(1.0, score), 4),
            matching_factors=matching_factors,
            outcome=historical_change.outcome,
            incident_occurred=historical_change.incident_occurred,
            root_cause=historical_change.root_cause,
            downtime_minutes=historical_change.downtime_minutes,
            lessons_learned=historical_change.lessons_learned,
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

    def _root_cause_score(self, change_request: ChangeRequest, root_cause: str) -> tuple[float, list[str]]:
        root_cause_tokens = self._tokens(root_cause.replace("_", " "))
        change_tokens = self._tokens(
            " ".join(
                [
                    change_request.title,
                    change_request.description,
                    change_request.affected_scope,
                    change_request.rollback_plan,
                ]
            )
        )
        matches = sorted(root_cause_tokens & change_tokens)
        if matches:
            return 1.0, matches
        return 0.5, []

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
    )
