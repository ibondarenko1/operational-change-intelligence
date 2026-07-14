"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { OutcomeBadge, RiskBadge } from "@/components/Badges";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateBlocks";
import {
  api,
  ApiError,
  ChangeRequest,
  formatLabel,
  RiskAssessment,
  SimilarHistoricalChange,
} from "@/lib/api";

export default function ChangeDetailsPage() {
  const params = useParams<{ id: string }>();
  const changeId = params.id;
  const [change, setChange] = useState<ChangeRequest | null>(null);
  const [assessment, setAssessment] = useState<RiskAssessment | null>(null);
  const [similar, setSimilar] = useState<SimilarHistoricalChange[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [changeResponse, similarResponse] = await Promise.all([
        api.getChange(changeId),
        api.getSimilar(changeId, 8),
      ]);
      setChange(changeResponse);
      setSimilar(similarResponse);

      try {
        const assessmentResponse = await api.getAssessment(changeId);
        setAssessment(assessmentResponse);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setAssessment(null);
        } else {
          throw err;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load change details");
    } finally {
      setLoading(false);
    }
  }, [changeId]);

  useEffect(() => {
    load();
  }, [load]);

  async function runAnalysis() {
    setAnalyzing(true);
    setError(null);
    try {
      const result = await api.analyzeChange(changeId);
      setAssessment(result);
      setSimilar(await api.getSimilar(changeId, 8));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to analyze change");
    } finally {
      setAnalyzing(false);
    }
  }

  if (loading) {
    return <LoadingState title="Loading change details" />;
  }

  if (error) {
    return <ErrorState title="Change details unavailable" message={error} />;
  }

  if (!change) {
    return <EmptyState title="Change not found" message="The requested change request does not exist." />;
  }

  const incidents = similar.filter((item) => item.outcome === "failed" || item.incident_occurred);

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <h1>{change.title}</h1>
          <p>
            {formatLabel(change.environment)} / {formatLabel(change.change_type)} /{" "}
            {formatLabel(change.status)}
          </p>
        </div>
        <div className="actions">
          <button className="button" type="button" onClick={runAnalysis} disabled={analyzing}>
            {analyzing ? "Analyzing" : "Run analysis"}
          </button>
          <Link className="button-secondary" href="/changes/new">
            New Change
          </Link>
        </div>
      </header>

      <section className="section grid-2">
        <div>
          <h2>Description</h2>
          <p>{change.description}</p>
          <h3>Affected scope</h3>
          <p>{change.affected_scope}</p>
        </div>
        <div>
          <h2>Implementation</h2>
          <p>
            <strong>Planned:</strong> {new Date(change.planned_start).toLocaleString()} -{" "}
            {new Date(change.planned_end).toLocaleString()}
          </p>
          <p>
            <strong>Rollback:</strong> {change.rollback_plan}
          </p>
          <p className="muted">
            Maintenance window: {change.maintenance_window ? "yes" : "no"} / Pilot:{" "}
            {change.pilot_enabled ? "yes" : "no"} / Report-only: {change.report_only_mode ? "yes" : "no"}
          </p>
        </div>
      </section>

      {assessment ? (
        <section className="section grid-2">
          <div className="score-block">
            <h2>Risk Assessment</h2>
            <span className="score-number">{assessment.score}</span>
            <RiskBadge level={assessment.level} />
            <strong>{formatLabel(assessment.recommendation)}</strong>
            <span className="muted">Confidence: {Math.round(assessment.confidence * 100)}%</span>
            <div className="formula">{assessment.formula}</div>
          </div>
          <div>
            <h2>Risk Factors</h2>
            {assessment.risk_factors.length === 0 ? (
              <EmptyState title="No risk factors" message="No deterministic rules were triggered." />
            ) : (
              <ul className="list">
                {assessment.risk_factors.map((factor) => (
                  <li className="list-item" key={factor.id}>
                    <header>
                      <strong>{factor.title}</strong>
                      <span className="points">{factor.points > 0 ? `+${factor.points}` : factor.points}</span>
                    </header>
                    <p>{factor.description}</p>
                    <p>
                      <strong>Evidence:</strong> {factor.evidence ?? "No evidence recorded"}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      ) : (
        <EmptyState
          title="No assessment yet"
          message="Run analysis to calculate risk score, factors, evidence, and checklist."
        />
      )}

      {assessment ? (
        <section className="section">
          <div className="section-header">
            <div>
              <h2>Checklist</h2>
              <p>Generated from triggered deterministic rules.</p>
            </div>
          </div>
          {assessment.checklist_items.length === 0 ? (
            <EmptyState title="No checklist items" message="No rule generated a checklist item." />
          ) : (
            <ul className="list">
              {assessment.checklist_items.map((item) => (
                <li className="list-item" key={item.id}>
                  <header>
                    <strong>{item.title}</strong>
                    <span className="badge risk-medium">{item.priority}</span>
                  </header>
                  <p>{item.description}</p>
                  <p className="muted">Status: {formatLabel(item.status)}</p>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      <section className="section">
        <div className="section-header">
          <div>
            <h2>Similar Historical Changes</h2>
            <p>Deterministic similarity score and matching factors.</p>
          </div>
        </div>
        {similar.length === 0 ? (
          <EmptyState title="No similar changes" message="Seed historical changes to compare this request." />
        ) : (
          <ul className="list">
            {similar.map((item) => (
              <li className="list-item" key={item.historical_change_id}>
                <header>
                  <strong>{item.title}</strong>
                  <span className="points">{item.similarity_score.toFixed(2)}</span>
                </header>
                <OutcomeBadge outcome={item.outcome} incident={item.incident_occurred} />
                <p>
                  <strong>Why similar:</strong> {item.matching_factors.join("; ")}
                </p>
                <p>
                  <strong>Lessons:</strong> {item.lessons_learned ?? "No lesson recorded"}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <h2>Past Incidents</h2>
            <p>Similar failed or incident historical records.</p>
          </div>
        </div>
        {incidents.length === 0 ? (
          <EmptyState title="No past incidents in similar results" message="No failed similar changes were returned." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Change</th>
                  <th>Root cause</th>
                  <th>Downtime</th>
                  <th>Lessons learned</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((incident) => (
                  <tr key={incident.historical_change_id}>
                    <td>{incident.title}</td>
                    <td>{formatLabel(incident.root_cause)}</td>
                    <td>{incident.downtime_minutes}m</td>
                    <td>{incident.lessons_learned ?? "None"}</td>
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
