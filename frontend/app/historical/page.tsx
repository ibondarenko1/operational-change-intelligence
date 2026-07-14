"use client";

import { useEffect, useState } from "react";

import { OutcomeBadge } from "@/components/Badges";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateBlocks";
import {
  api,
  changeTypes,
  environments,
  formatLabel,
  HistoricalChange,
  HistoricalFilters,
} from "@/lib/api";

export default function HistoricalChangesPage() {
  const [filters, setFilters] = useState<HistoricalFilters>({});
  const [records, setRecords] = useState<HistoricalChange[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await api.listHistorical(filters, 100);
        if (active) {
          setRecords(response);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Unable to load historical changes");
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
  }, [filters]);

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <h1>Historical Changes</h1>
          <p>Structured historical change records used by risk, similarity, and human-error analytics.</p>
        </div>
      </header>

      <section className="section">
        <div className="filters">
          <select
            aria-label="Environment"
            value={filters.environment ?? ""}
            onChange={(event) => setFilters({ ...filters, environment: event.target.value as HistoricalFilters["environment"] })}
          >
            <option value="">All environments</option>
            {environments.map((environment) => (
              <option key={environment} value={environment}>
                {formatLabel(environment)}
              </option>
            ))}
          </select>
          <select
            aria-label="Change type"
            value={filters.change_type ?? ""}
            onChange={(event) => setFilters({ ...filters, change_type: event.target.value as HistoricalFilters["change_type"] })}
          >
            <option value="">All change types</option>
            {changeTypes.map((changeType) => (
              <option key={changeType} value={changeType}>
                {formatLabel(changeType)}
              </option>
            ))}
          </select>
          <select
            aria-label="Outcome"
            value={filters.outcome ?? ""}
            onChange={(event) => setFilters({ ...filters, outcome: event.target.value })}
          >
            <option value="">All outcomes</option>
            <option value="successful">Successful</option>
            <option value="failed">Failed</option>
          </select>
          <select
            aria-label="Incident"
            value={filters.incident_occurred ?? ""}
            onChange={(event) =>
              setFilters({ ...filters, incident_occurred: event.target.value as HistoricalFilters["incident_occurred"] })
            }
          >
            <option value="">All incident states</option>
            <option value="true">Incident occurred</option>
            <option value="false">No incident</option>
          </select>
          <input
            aria-label="Root cause"
            placeholder="root cause"
            value={filters.root_cause ?? ""}
            onChange={(event) => setFilters({ ...filters, root_cause: event.target.value })}
          />
        </div>
        <button className="button-secondary" type="button" onClick={() => setFilters({})}>
          Clear filters
        </button>
      </section>

      {loading ? <LoadingState title="Loading historical changes" /> : null}
      {error ? <ErrorState title="Historical changes unavailable" message={error} /> : null}

      {!loading && !error ? (
        records.length === 0 ? (
          <EmptyState title="No records match filters" message="Adjust filters or seed demo historical changes." />
        ) : (
          <section className="section">
            <div className="section-header">
              <h2>{records.length} records</h2>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Environment</th>
                    <th>Type</th>
                    <th>Outcome</th>
                    <th>Root cause</th>
                    <th>Downtime</th>
                    <th>Rollback</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((record) => (
                    <tr key={record.id}>
                      <td>{record.title}</td>
                      <td>{formatLabel(record.environment)}</td>
                      <td>{formatLabel(record.change_type)}</td>
                      <td>
                        <OutcomeBadge outcome={record.outcome} incident={record.incident_occurred} />
                      </td>
                      <td>{formatLabel(record.root_cause)}</td>
                      <td>{record.downtime_minutes}m</td>
                      <td>{record.rollback_required ? "yes" : "no"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )
      ) : null}
    </div>
  );
}
