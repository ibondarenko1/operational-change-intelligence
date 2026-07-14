"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/components/StateBlocks";
import { MetricCard } from "@/components/MetricCard";
import { api, AnalyticsSummary, ChangeRequest, formatLabel } from "@/lib/api";

export default function DashboardPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [changes, setChanges] = useState<ChangeRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [summaryResponse, changesResponse] = await Promise.all([
          api.getSummary(),
          api.listChanges(5),
        ]);
        if (!active) {
          return;
        }
        setSummary(summaryResponse);
        setChanges(changesResponse);
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Unable to load dashboard");
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
    return <LoadingState title="Loading dashboard" />;
  }

  if (error) {
    return <ErrorState title="Dashboard unavailable" message={error} />;
  }

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>Operational change health, current historical risk profile, and recent change requests.</p>
        </div>
        <Link className="button" href="/changes/new">
          New Change
        </Link>
      </header>

      {summary ? (
        <section className="metrics-grid">
          <MetricCard label="Total changes" value={summary.total_changes} />
          <MetricCard label="Failure rate" value={`${summary.failure_rate}%`} />
          <MetricCard label="Average downtime" value={`${summary.average_downtime_minutes}m`} />
          <MetricCard label="Most common root cause" value={formatLabel(summary.most_common_root_cause)} />
          <MetricCard label="Highest-risk change type" value={formatLabel(summary.highest_risk_change_type)} />
        </section>
      ) : (
        <EmptyState title="No analytics available" message="Seed historical changes to populate the dashboard." />
      )}

      <section className="section">
        <div className="section-header">
          <div>
            <h2>Recent Change Requests</h2>
            <p>Latest planned changes submitted for review.</p>
          </div>
        </div>

        {changes.length === 0 ? (
          <EmptyState title="No change requests" message="Create a change request to start risk analysis." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Environment</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Planned start</th>
                </tr>
              </thead>
              <tbody>
                {changes.map((change) => (
                  <tr key={change.id}>
                    <td>
                      <Link className="link" href={`/changes/${change.id}`}>
                        {change.title}
                      </Link>
                    </td>
                    <td>{formatLabel(change.environment)}</td>
                    <td>{formatLabel(change.change_type)}</td>
                    <td>{formatLabel(change.status)}</td>
                    <td className="nowrap">{new Date(change.planned_start).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
