"use client";

import { useEffect, useState } from "react";

import { MetricCard } from "@/components/MetricCard";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateBlocks";
import {
  AnalyticsSummary,
  api,
  ChangeTypeAnalytics,
  FailurePattern,
  formatLabel,
  RootCauseAnalytics,
} from "@/lib/api";

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [rootCauses, setRootCauses] = useState<RootCauseAnalytics[]>([]);
  const [changeTypes, setChangeTypes] = useState<ChangeTypeAnalytics[]>([]);
  const [patterns, setPatterns] = useState<FailurePattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [summaryResponse, rootCauseResponse, changeTypeResponse, patternResponse] = await Promise.all([
          api.getSummary(),
          api.getRootCauses(),
          api.getChangeTypeAnalytics(),
          api.getFailurePatterns(),
        ]);
        if (!active) {
          return;
        }
        setSummary(summaryResponse);
        setRootCauses(rootCauseResponse);
        setChangeTypes(changeTypeResponse);
        setPatterns(patternResponse);
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Unable to load analytics");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return <LoadingState title="Loading analytics" />;
  }

  if (error) {
    return <ErrorState title="Analytics unavailable" message={error} />;
  }

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <h1>Human Error Analytics</h1>
          <p>Deterministic analysis of recurring operational failure patterns in historical changes.</p>
        </div>
      </header>

      {summary ? (
        <section className="metrics-grid">
          <MetricCard label="Total changes" value={summary.total_changes} />
          <MetricCard label="Failure rate" value={`${summary.failure_rate}%`} />
          <MetricCard label="Average downtime" value={`${summary.average_downtime_minutes}m`} />
          <MetricCard label="Most common root cause" value={formatLabel(summary.most_common_root_cause)} />
          <MetricCard label="Highest-risk type" value={formatLabel(summary.highest_risk_change_type)} />
        </section>
      ) : (
        <EmptyState title="No summary" message="No historical changes are available." />
      )}

      <section className="section">
        <div className="section-header">
          <div>
            <h2>Root Causes</h2>
            <p>Recurring causes behind failed or incident changes.</p>
          </div>
        </div>
        {rootCauses.length === 0 ? (
          <EmptyState title="No root causes" message="No failed changes with root causes were found." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Root cause</th>
                  <th>Count</th>
                  <th>Share</th>
                  <th>Avg downtime</th>
                  <th>Rollback rate</th>
                  <th>Affected types</th>
                </tr>
              </thead>
              <tbody>
                {rootCauses.map((item) => (
                  <tr key={item.root_cause}>
                    <td>{formatLabel(item.root_cause)}</td>
                    <td>{item.count}</td>
                    <td>{item.percentage}%</td>
                    <td>{item.average_downtime}m</td>
                    <td>{item.rollback_rate}%</td>
                    <td>{item.affected_change_types.map(formatLabel).join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <h2>Failure Rate by Change Type</h2>
            <p>Operational reliability grouped by change category.</p>
          </div>
        </div>
        {changeTypes.length === 0 ? (
          <EmptyState title="No change type analytics" message="No historical changes are available." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Change type</th>
                  <th>Total</th>
                  <th>Successful</th>
                  <th>Failed</th>
                  <th>Failure rate</th>
                  <th>Avg downtime</th>
                  <th>Common root causes</th>
                </tr>
              </thead>
              <tbody>
                {changeTypes.map((item) => (
                  <tr key={item.change_type}>
                    <td>{formatLabel(item.change_type)}</td>
                    <td>{item.total}</td>
                    <td>{item.successful}</td>
                    <td>{item.failed}</td>
                    <td>{item.failure_rate}%</td>
                    <td>{item.average_downtime}m</td>
                    <td>{item.common_root_causes.map(formatLabel).join(", ") || "None"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <h2>Repeated Failure Patterns</h2>
            <p>High downtime, high failure-rate, rollback-heavy, and repeated-error clusters.</p>
          </div>
        </div>
        {patterns.length === 0 ? (
          <EmptyState title="No repeated patterns" message="No failure pattern crossed the deterministic thresholds." />
        ) : (
          <ul className="list">
            {patterns.map((pattern) => (
              <li className="list-item" key={`${pattern.pattern_type}-${pattern.title}`}>
                <header>
                  <strong>{pattern.title}</strong>
                  <span className="points">{pattern.severity_score}</span>
                </header>
                <p>{pattern.description}</p>
                <p>
                  <strong>Type:</strong> {formatLabel(pattern.pattern_type)} / <strong>Count:</strong>{" "}
                  {pattern.count}
                  {pattern.rate !== null ? ` / Rate: ${pattern.rate}%` : ""}
                  {pattern.average_downtime !== null ? ` / Avg downtime: ${pattern.average_downtime}m` : ""}
                </p>
                <p>
                  <strong>Evidence:</strong> {pattern.evidence.join("; ")}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
