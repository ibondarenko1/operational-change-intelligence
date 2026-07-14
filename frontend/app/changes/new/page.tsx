"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";

import { ErrorState } from "@/components/StateBlocks";
import { api, changeTypes, ChangeRequestCreate, environments, formatLabel } from "@/lib/api";

function toDateTimeLocal(date: Date): string {
  const offset = date.getTimezoneOffset();
  const localDate = new Date(date.getTime() - offset * 60_000);
  return localDate.toISOString().slice(0, 16);
}

function toIso(value: string): string {
  return new Date(value).toISOString();
}

export default function NewChangePage() {
  const router = useRouter();
  const defaults = useMemo(() => {
    const start = new Date();
    start.setMinutes(0, 0, 0);
    start.setHours(start.getHours() + 2);
    const end = new Date(start.getTime() + 60 * 60_000);
    return {
      start: toDateTimeLocal(start),
      end: toDateTimeLocal(end),
    };
  }, []);

  const [form, setForm] = useState({
    title: "",
    description: "",
    environment: "entra_id",
    change_type: "mfa_rollout",
    planned_start: defaults.start,
    planned_end: defaults.end,
    affected_scope: "",
    rollback_plan: "",
    maintenance_window: true,
    pilot_enabled: false,
    report_only_mode: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function loadDemoScenario() {
    setForm({
      title: "Enable MFA for all contractors",
      description: "Require MFA for all external contractor accounts and block legacy authentication.",
      environment: "entra_id",
      change_type: "mfa_rollout",
      planned_start: defaults.start,
      planned_end: defaults.end,
      affected_scope: "All contractor accounts, VPN access, Microsoft 365, legacy business applications.",
      rollback_plan: "Disable the new Conditional Access policy.",
      maintenance_window: false,
      pilot_enabled: false,
      report_only_mode: false,
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    const payload: ChangeRequestCreate = {
      ...form,
      environment: form.environment as ChangeRequestCreate["environment"],
      change_type: form.change_type as ChangeRequestCreate["change_type"],
      planned_start: toIso(form.planned_start),
      planned_end: toIso(form.planned_end),
      status: "draft",
    };

    try {
      const created = await api.createChange(payload);
      router.push(`/changes/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create change request");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <h1>New Change</h1>
          <p>Capture the planned Microsoft security change before running deterministic risk analysis.</p>
        </div>
        <button className="button-secondary" type="button" onClick={loadDemoScenario}>
          Load demo scenario
        </button>
      </header>

      {error ? <ErrorState title="Create failed" message={error} /> : null}

      <form className="section form-grid" onSubmit={handleSubmit}>
        <div className="form-field full">
          <label htmlFor="title">Title</label>
          <input
            id="title"
            required
            value={form.title}
            onChange={(event) => setForm({ ...form, title: event.target.value })}
            placeholder="Enable MFA for all contractors"
          />
        </div>

        <div className="form-field">
          <label htmlFor="environment">Environment</label>
          <select
            id="environment"
            value={form.environment}
            onChange={(event) => setForm({ ...form, environment: event.target.value })}
          >
            {environments.map((environment) => (
              <option key={environment} value={environment}>
                {formatLabel(environment)}
              </option>
            ))}
          </select>
        </div>

        <div className="form-field">
          <label htmlFor="change_type">Change type</label>
          <select
            id="change_type"
            value={form.change_type}
            onChange={(event) => setForm({ ...form, change_type: event.target.value })}
          >
            {changeTypes.map((changeType) => (
              <option key={changeType} value={changeType}>
                {formatLabel(changeType)}
              </option>
            ))}
          </select>
        </div>

        <div className="form-field">
          <label htmlFor="planned_start">Planned start</label>
          <input
            id="planned_start"
            type="datetime-local"
            required
            value={form.planned_start}
            onChange={(event) => setForm({ ...form, planned_start: event.target.value })}
          />
        </div>

        <div className="form-field">
          <label htmlFor="planned_end">Planned end</label>
          <input
            id="planned_end"
            type="datetime-local"
            required
            value={form.planned_end}
            onChange={(event) => setForm({ ...form, planned_end: event.target.value })}
          />
        </div>

        <div className="form-field full">
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            required
            value={form.description}
            onChange={(event) => setForm({ ...form, description: event.target.value })}
            placeholder="What will change, how it will be implemented, and what dependencies are expected?"
          />
        </div>

        <div className="form-field full">
          <label htmlFor="affected_scope">Affected scope</label>
          <textarea
            id="affected_scope"
            required
            value={form.affected_scope}
            onChange={(event) => setForm({ ...form, affected_scope: event.target.value })}
            placeholder="All contractors and vendor accounts"
          />
        </div>

        <div className="form-field full">
          <label htmlFor="rollback_plan">Rollback plan</label>
          <textarea
            id="rollback_plan"
            required
            value={form.rollback_plan}
            onChange={(event) => setForm({ ...form, rollback_plan: event.target.value })}
            placeholder="Disable the new policy, restore previous assignments, and validate sign-ins."
          />
        </div>

        <div className="form-field full">
          <div className="checkbox-row">
            <label>
              <input
                type="checkbox"
                checked={form.maintenance_window}
                onChange={(event) => setForm({ ...form, maintenance_window: event.target.checked })}
              />
              Maintenance window
            </label>
            <label>
              <input
                type="checkbox"
                checked={form.pilot_enabled}
                onChange={(event) => setForm({ ...form, pilot_enabled: event.target.checked })}
              />
              Pilot enabled
            </label>
            <label>
              <input
                type="checkbox"
                checked={form.report_only_mode}
                onChange={(event) => setForm({ ...form, report_only_mode: event.target.checked })}
              />
              Report-only mode
            </label>
          </div>
        </div>

        <div className="form-field full actions">
          <button className="button" type="submit" disabled={submitting}>
            {submitting ? "Creating" : "Create change"}
          </button>
        </div>
      </form>
    </div>
  );
}
