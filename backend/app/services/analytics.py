from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.change import HistoricalChange
from app.models.enums import ChangeType, Environment
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    ChangeTypeAnalyticsResponse,
    FailurePatternResponse,
    RootCauseAnalyticsResponse,
)


class AnalyticsService:
    def get_summary(
        self,
        db: Session,
        environment: Environment | None = None,
        change_type: ChangeType | None = None,
    ) -> AnalyticsSummaryResponse:
        records = self._load_records(db, environment=environment, change_type=change_type)
        total = len(records)
        successful = sum(1 for record in records if self._is_successful(record))
        failed = sum(1 for record in records if self._is_failed(record))
        incidents = sum(1 for record in records if record.incident_occurred)
        root_causes = self.get_root_causes(db, environment=environment, change_type=change_type)
        change_types = self.get_change_types(db, environment=environment, change_type=change_type)

        highest_risk_change_type = None
        if change_types:
            highest_risk_change_type = max(
                change_types,
                key=lambda item: (
                    item.failure_rate,
                    item.failed,
                    item.average_downtime,
                    self._enum_value(item.change_type),
                ),
            ).change_type

        return AnalyticsSummaryResponse(
            total_changes=total,
            successful_changes=successful,
            failed_changes=failed,
            failure_rate=self._rate(failed, total),
            changes_with_incidents=incidents,
            average_downtime_minutes=self._average([record.downtime_minutes for record in records]),
            most_common_root_cause=root_causes[0].root_cause if root_causes else None,
            highest_risk_change_type=highest_risk_change_type,
            common_process_failures=self._common_optional_values(records, "process_failure"),
            common_preventive_controls=self._common_optional_values(records, "preventive_control"),
            common_business_impacts=self._common_optional_values(records, "business_impact"),
        )

    def get_root_causes(
        self,
        db: Session,
        environment: Environment | None = None,
        change_type: ChangeType | None = None,
    ) -> list[RootCauseAnalyticsResponse]:
        records = self._load_records(db, environment=environment, change_type=change_type)
        failure_records = [record for record in records if self._is_failed(record) or record.incident_occurred]
        grouped: dict[str, list[HistoricalChange]] = defaultdict(list)

        for record in failure_records:
            if record.root_cause:
                grouped[record.root_cause].append(record)

        total_with_root_cause = sum(len(items) for items in grouped.values())
        results = [
            RootCauseAnalyticsResponse(
                root_cause=root_cause,
                count=len(items),
                percentage=self._rate(len(items), total_with_root_cause),
                average_downtime=self._average([item.downtime_minutes for item in items]),
                rollback_rate=self._rate(sum(1 for item in items if item.rollback_required), len(items)),
                affected_change_types=sorted(
                    {item.change_type for item in items},
                    key=self._enum_value,
                ),
            )
            for root_cause, items in grouped.items()
        ]
        return sorted(
            results,
            key=lambda item: (-item.count, item.root_cause),
        )

    def get_change_types(
        self,
        db: Session,
        environment: Environment | None = None,
        change_type: ChangeType | None = None,
    ) -> list[ChangeTypeAnalyticsResponse]:
        records = self._load_records(db, environment=environment, change_type=change_type)
        grouped: dict[ChangeType, list[HistoricalChange]] = defaultdict(list)

        for record in records:
            grouped[record.change_type].append(record)

        results = []
        for grouped_change_type, items in grouped.items():
            successful = sum(1 for item in items if self._is_successful(item))
            failed = sum(1 for item in items if self._is_failed(item))
            root_cause_counts = Counter(item.root_cause for item in items if item.root_cause)
            common_root_causes = [
                root_cause
                for root_cause, _ in sorted(
                    root_cause_counts.items(),
                    key=lambda entry: (-entry[1], entry[0]),
                )
            ]
            results.append(
                ChangeTypeAnalyticsResponse(
                    change_type=grouped_change_type,
                    total=len(items),
                    successful=successful,
                    failed=failed,
                    failure_rate=self._rate(failed, len(items)),
                    average_downtime=self._average([item.downtime_minutes for item in items]),
                    common_root_causes=common_root_causes,
                )
            )

        return sorted(
            results,
            key=lambda item: (-item.failure_rate, -item.failed, -item.average_downtime, self._enum_value(item.change_type)),
        )

    def get_failure_patterns(
        self,
        db: Session,
        environment: Environment | None = None,
        change_type: ChangeType | None = None,
    ) -> list[FailurePatternResponse]:
        root_causes = self.get_root_causes(db, environment=environment, change_type=change_type)
        change_types = self.get_change_types(db, environment=environment, change_type=change_type)
        patterns: list[FailurePatternResponse] = []

        patterns.extend(self._repeated_root_cause_patterns(root_causes))
        patterns.extend(self._high_failure_rate_patterns(change_types))
        patterns.extend(self._frequent_rollback_patterns(db, environment, change_type))
        patterns.extend(self._high_downtime_patterns(db, environment, change_type))
        patterns.extend(self._repeated_error_patterns(change_types, root_causes))
        patterns.extend(self._repeated_causal_chain_patterns(db, environment, change_type))

        deduped = {(pattern.pattern_type, pattern.title): pattern for pattern in patterns}
        return sorted(
            deduped.values(),
            key=lambda item: (-item.severity_score, item.pattern_type, item.title),
        )

    def _repeated_root_cause_patterns(
        self,
        root_causes: list[RootCauseAnalyticsResponse],
    ) -> list[FailurePatternResponse]:
        return [
            FailurePatternResponse(
                pattern_type="repeated_root_cause",
                title=f"Repeated root cause: {item.root_cause}",
                description=f"{item.root_cause} appeared in {item.count} failed or incident changes.",
                count=item.count,
                rate=item.percentage,
                average_downtime=item.average_downtime,
                severity_score=round(item.count * 10 + item.average_downtime / 10 + item.rollback_rate / 10, 2),
                affected_change_types=item.affected_change_types,
                root_causes=[item.root_cause],
                evidence=[
                    f"count={item.count}",
                    f"percentage={item.percentage}%",
                    f"rollback_rate={item.rollback_rate}%",
                ],
            )
            for item in root_causes
            if item.count >= 2
        ]

    def _high_failure_rate_patterns(
        self,
        change_types: list[ChangeTypeAnalyticsResponse],
    ) -> list[FailurePatternResponse]:
        return [
            FailurePatternResponse(
                pattern_type="high_failure_rate_change_type",
                title=f"High failure rate: {item.change_type.value}",
                description=f"{item.change_type.value} has a {item.failure_rate}% failure rate.",
                count=item.failed,
                rate=item.failure_rate,
                average_downtime=item.average_downtime,
                severity_score=round(item.failure_rate + item.failed * 5 + item.average_downtime / 10, 2),
                affected_change_types=[item.change_type],
                root_causes=item.common_root_causes,
                evidence=[
                    f"failed={item.failed}",
                    f"total={item.total}",
                    f"average_downtime={item.average_downtime}",
                ],
            )
            for item in change_types
            if item.total >= 3 and item.failure_rate >= 50
        ]

    def _frequent_rollback_patterns(
        self,
        db: Session,
        environment: Environment | None,
        change_type: ChangeType | None,
    ) -> list[FailurePatternResponse]:
        records = self._load_records(db, environment=environment, change_type=change_type)
        grouped = self._group_by_change_type(records)
        patterns = []

        for grouped_change_type, items in grouped.items():
            rollback_count = sum(1 for item in items if item.rollback_required)
            rollback_rate = self._rate(rollback_count, len(items))
            if len(items) < 3 or rollback_count < 2 or rollback_rate < 40:
                continue

            patterns.append(
                FailurePatternResponse(
                    pattern_type="frequent_rollback_change_type",
                    title=f"Frequent rollback: {grouped_change_type.value}",
                    description=f"{grouped_change_type.value} required rollback in {rollback_rate}% of changes.",
                    count=rollback_count,
                    rate=rollback_rate,
                    average_downtime=self._average([item.downtime_minutes for item in items]),
                    severity_score=round(rollback_rate + rollback_count * 5, 2),
                    affected_change_types=[grouped_change_type],
                    root_causes=self._common_root_causes(items),
                    evidence=[
                        f"rollback_count={rollback_count}",
                        f"total={len(items)}",
                    ],
                )
            )

        return patterns

    def _high_downtime_patterns(
        self,
        db: Session,
        environment: Environment | None,
        change_type: ChangeType | None,
    ) -> list[FailurePatternResponse]:
        records = self._load_records(db, environment=environment, change_type=change_type)
        grouped = self._group_by_change_type(records)
        patterns = []

        for grouped_change_type, items in grouped.items():
            failed_items = [item for item in items if self._is_failed(item) or item.incident_occurred]
            average_failed_downtime = self._average([item.downtime_minutes for item in failed_items])
            if not failed_items or average_failed_downtime < 100:
                continue

            patterns.append(
                FailurePatternResponse(
                    pattern_type="high_downtime_change_type",
                    title=f"High downtime: {grouped_change_type.value}",
                    description=f"{grouped_change_type.value} failures average {average_failed_downtime} minutes of downtime.",
                    count=len(failed_items),
                    rate=None,
                    average_downtime=average_failed_downtime,
                    severity_score=round(average_failed_downtime + len(failed_items) * 5, 2),
                    affected_change_types=[grouped_change_type],
                    root_causes=self._common_root_causes(failed_items),
                    evidence=[
                        f"failed_or_incident_count={len(failed_items)}",
                    ],
                )
            )

        return patterns

    def _repeated_error_patterns(
        self,
        change_types: list[ChangeTypeAnalyticsResponse],
        root_causes: list[RootCauseAnalyticsResponse],
    ) -> list[FailurePatternResponse]:
        patterns = [
            FailurePatternResponse(
                pattern_type="repeated_error_cluster",
                title=f"At least three failures: {item.change_type.value}",
                description=f"{item.change_type.value} failed {item.failed} times.",
                count=item.failed,
                rate=item.failure_rate,
                average_downtime=item.average_downtime,
                severity_score=round(item.failed * 15 + item.failure_rate, 2),
                affected_change_types=[item.change_type],
                root_causes=item.common_root_causes,
                evidence=[
                    "minimum_repetition_threshold=3",
                    f"failed={item.failed}",
                ],
            )
            for item in change_types
            if item.failed >= 3
        ]

        patterns.extend(
            FailurePatternResponse(
                pattern_type="repeated_error_cluster",
                title=f"At least three root-cause repeats: {item.root_cause}",
                description=f"{item.root_cause} repeated {item.count} times.",
                count=item.count,
                rate=item.percentage,
                average_downtime=item.average_downtime,
                severity_score=round(item.count * 15 + item.average_downtime / 10, 2),
                affected_change_types=item.affected_change_types,
                root_causes=[item.root_cause],
                evidence=[
                    "minimum_repetition_threshold=3",
                    f"count={item.count}",
                ],
            )
            for item in root_causes
            if item.count >= 3
        )

        return patterns

    def _repeated_causal_chain_patterns(
        self,
        db: Session,
        environment: Environment | None,
        change_type: ChangeType | None,
    ) -> list[FailurePatternResponse]:
        records = [
            record
            for record in self._load_records(db, environment=environment, change_type=change_type)
            if self._is_failed(record) or record.incident_occurred
        ]
        grouped: dict[tuple[str, str, str], list[HistoricalChange]] = defaultdict(list)
        for record in records:
            if not record.process_failure or not record.technical_cause or not record.business_impact:
                continue
            grouped[
                (
                    record.process_failure,
                    record.technical_cause,
                    record.business_impact,
                )
            ].append(record)

        patterns = []
        for (process_failure, technical_cause, business_impact), items in grouped.items():
            if len(items) < 2:
                continue
            preventive_controls = self._common_optional_values(items, "preventive_control")
            patterns.append(
                FailurePatternResponse(
                    pattern_type="repeated_causal_chain",
                    title=f"Repeated causal chain: {process_failure}",
                    description=(
                        f"{process_failure} led to '{technical_cause}' and business impact "
                        f"'{business_impact}' in {len(items)} changes."
                    ),
                    count=len(items),
                    rate=self._rate(len(items), len(records)),
                    average_downtime=self._average([item.downtime_minutes for item in items]),
                    severity_score=round(len(items) * 20 + self._average([item.downtime_minutes for item in items]) / 10, 2),
                    affected_change_types=sorted({item.change_type for item in items}, key=self._enum_value),
                    root_causes=self._common_root_causes(items),
                    evidence=[item.title for item in items[:5]],
                    process_failure=process_failure,
                    technical_cause=technical_cause,
                    business_impact=business_impact,
                    preventive_control=preventive_controls[0] if preventive_controls else None,
                )
            )

        return patterns

    def _load_records(
        self,
        db: Session,
        environment: Environment | None = None,
        change_type: ChangeType | None = None,
    ) -> list[HistoricalChange]:
        statement = select(HistoricalChange)
        if environment is not None:
            statement = statement.where(HistoricalChange.environment == environment)
        if change_type is not None:
            statement = statement.where(HistoricalChange.change_type == change_type)
        statement = statement.order_by(HistoricalChange.created_at.asc(), HistoricalChange.title.asc())
        return list(db.scalars(statement).all())

    def _group_by_change_type(
        self,
        records: list[HistoricalChange],
    ) -> dict[ChangeType, list[HistoricalChange]]:
        grouped: dict[ChangeType, list[HistoricalChange]] = defaultdict(list)
        for record in records:
            grouped[record.change_type].append(record)
        return grouped

    def _common_root_causes(self, records: list[HistoricalChange]) -> list[str]:
        root_cause_counts = Counter(record.root_cause for record in records if record.root_cause)
        return [
            root_cause
            for root_cause, _ in sorted(root_cause_counts.items(), key=lambda entry: (-entry[1], entry[0]))
        ]

    def _common_optional_values(self, records: list[HistoricalChange], field_name: str) -> list[str]:
        values = Counter(
            getattr(record, field_name)
            for record in records
            if (self._is_failed(record) or record.incident_occurred) and getattr(record, field_name)
        )
        return [value for value, _ in sorted(values.items(), key=lambda entry: (-entry[1], entry[0]))[:5]]

    def _is_successful(self, record: HistoricalChange) -> bool:
        return record.outcome == "successful"

    def _is_failed(self, record: HistoricalChange) -> bool:
        return record.outcome == "failed"

    def _rate(self, count: int, total: int) -> float:
        if total == 0:
            return 0.0
        return round((count / total) * 100, 2)

    def _average(self, values: list[int]) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)

    def _enum_value(self, value: ChangeType | Environment | str) -> str:
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)
