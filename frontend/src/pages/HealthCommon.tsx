import type { ChangeEvent, ReactNode } from "react";
import type { Astronaut } from "../types";

export function CrewPicker({ crew, value, onChange }: { crew: Astronaut[]; value: string; onChange: (id: string) => void }) {
  return <label className="crew-picker"><span>Crew member</span><select value={value} onChange={(event: ChangeEvent<HTMLSelectElement>) => onChange(event.target.value)} aria-label="Select crew member">
    {crew.map((person) => <option key={person.id} value={person.id}>{person.full_name} · {person.callsign}</option>)}
  </select></label>;
}

export function StateBadge({ status }: { status: string }) {
  const labels: Record<string, string> = { data_available: "Data available", insufficient: "Insufficient data", unavailable: "Unavailable", not_monitored: "Not monitored", awaiting_medical_review: "Awaiting review", verified: "Verified", not_verified: "Not verified", unverified: "Unreviewed", collecting: "Collecting", needs_more_data: "Needs more data", ready_for_review: "Ready for review", profile_active: "Profile active", not_started: "Not started" };
  return <span className={`state-badge state-${status}`}>{labels[status] || status.replace(/_/g, " ")}</span>;
}

export function ApiError({ error }: { error: unknown }) {
  if (!error) return null;
  const value = error as { message?: string; response?: { data?: { detail?: string } } };
  return <div role="alert" className="form-alert error">{value.response?.data?.detail || value.message || "The request could not be completed."}</div>;
}

export function CompactFact({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return <div className="compact-fact"><span>{label}</span><strong>{value}</strong>{hint && <small>{hint}</small>}</div>;
}
