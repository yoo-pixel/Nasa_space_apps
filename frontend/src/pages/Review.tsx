import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCheck, ClipboardCheck, ExternalLink, RotateCcw, Stethoscope } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { getAlerts, updateAlert } from "../services/alertService";
import { listAstronauts } from "../services/astronautService";
import { getBaselines, getMeasurements } from "../services/measurementService";
import { Avatar, DataNotice, EmptyState, ErrorState, formatStamp, LoadingState, PageTitle, Panel, prettyMetric, StatusPill } from "../components/Ui";

export default function Review() {
  const [params, setParams] = useSearchParams();
  const alerts = useQuery({ queryKey: ["alerts"], queryFn: () => getAlerts() });
  const crew = useQuery({ queryKey: ["crew"], queryFn: () => listAstronauts() });
  const selectedId = params.get("id") || alerts.data?.find((item) => item.status !== "resolved")?.id || alerts.data?.[0]?.id || "";
  const selected = alerts.data?.find((item) => item.id === selectedId);
  const person = crew.data?.find((item) => item.id === selected?.astronaut_id);
  const readings = useQuery({ queryKey: ["measurements", selected?.astronaut_id, "review"], queryFn: () => getMeasurements(selected!.astronaut_id), enabled: !!selected });
  const baselines = useQuery({ queryKey: ["baselines", selected?.astronaut_id], queryFn: () => getBaselines(selected!.astronaut_id), enabled: !!selected });
  const baseline = baselines.data?.find((item) => item.metric === selected?.metric);
  const [notes, setNotes] = useState("");
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const client = useQueryClient();
  useEffect(() => { setNotes(selected?.reviewer_notes || ""); }, [selectedId, selected?.reviewer_notes]);
  const mark = async (status: "acknowledged" | "resolved" | "open") => {
    if (!selected) return;
    setBusy(true); setFeedback("");
    try {
      await updateAlert(selected.id, { status, reviewer_notes: notes, reviewed_by: "Dr. Rivera" });
      await Promise.all([client.invalidateQueries({ queryKey: ["alerts"] }), client.invalidateQueries({ queryKey: ["alert-count"] }), client.invalidateQueries({ queryKey: ["dashboard"] })]);
      setFeedback("Review update saved to the backend.");
    } catch (e) { setFeedback((e as Error).message); }
    finally { setBusy(false); }
  };
  if (alerts.isLoading || crew.isLoading) return <LoadingState label="Loading review queue" />;
  if (alerts.error || crew.error) return <ErrorState message={((alerts.error || crew.error) as Error).message} />;
  return <div className="page-stack">
    <PageTitle eyebrow="CLINICAL WORKFLOW" title="Medical review" subtitle="Inspect source data and document a human assessment" />
    <DataNotice />
    {!alerts.data?.length ? <Panel title="Review queue"><EmptyState title="No alerts to review" detail="New baseline flags will appear here after analysis." /></Panel> : <div className="review-workspace">
      <Panel title="Review queue" detail="Select a flag to inspect">
        <div className="queue-list">{alerts.data.map((alert) => {
          const member = crew.data?.find((item) => item.id === alert.astronaut_id);
          return <button className={"queue-item " + (alert.id === selectedId ? "selected" : "")} key={alert.id} onClick={() => setParams({ id: alert.id })}>
            <Avatar name={member?.callsign || "Crew"} color={member?.avatar_color} size="sm" /><span className="queue-item-main"><strong>{member?.callsign || "Crew"} · {prettyMetric(alert.metric)}</strong><small>{alert.observed_value} {alert.unit} · {formatStamp(alert.created_at)}</small></span><StatusPill status={alert.status} />
          </button>;
        })}</div>
      </Panel>
      {selected && <div className="review-detail">
        <Panel title="Flag details" detail={selected.title} action={<StatusPill status={selected.status} />}>
          <div className="review-person-banner"><Avatar name={person?.full_name || "Crew"} color={person?.avatar_color} size="md" /><div><strong>{person?.full_name || "Crew member"}</strong><span>{person?.callsign} · {person?.mission?.name}</span></div><Link className="inline-link" to={"/crew/" + selected.astronaut_id}>Profile <ExternalLink size={13} /></Link></div>
          <div className="review-observation-grid"><div><span>Observed value</span><strong>{selected.observed_value} <small>{selected.unit}</small></strong></div><div><span>Personal median</span><strong>{selected.baseline_value ?? "—"} <small>{selected.unit}</small></strong></div><div><span>Personal band</span><strong>{baseline ? baseline.lower_bound + " – " + baseline.upper_bound : "—"} <small>{selected.unit}</small></strong></div><div><span>Recorded</span><strong>{formatStamp(selected.created_at)}</strong></div></div>
          <div className="explanation-box"><div className="analysis-summary-icon"><Stethoscope size={17} /></div><div><strong>Experimental baseline comparison</strong><p>{selected.explanation}</p><small>Statistical prompt only. Context, measurement quality, and clinical judgment are required.</small></div></div>
        </Panel>
        <Panel title="Related history" detail="Most recent measurements for this crew member and metric">
          {readings.isLoading ? <LoadingState /> : readings.data?.filter((r) => r.metric === selected.metric).slice(0, 8).length ? <div className="compact-records">{readings.data?.filter((r) => r.metric === selected.metric).slice(0, 8).map((reading) => <div key={reading.id}><span>{formatStamp(reading.measured_at)}</span><strong>{reading.value} {reading.unit}</strong><small>{reading.source_type}</small></div>)}</div> : <EmptyState title="No related measurements" detail="The source reading may not be available." />}
        </Panel>
        <Panel title="Medical review notes" detail="Notes are saved with the alert when you acknowledge or resolve it">
          <textarea className="review-notes" rows={4} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Record context, follow-up, or review rationale..." />
          {feedback && <div className="form-alert success">{feedback}</div>}
          <div className="review-actions">
            <button className="outline-button" disabled={busy} onClick={() => mark("acknowledged")}><CheckCheck size={14} /> Acknowledge</button>
            {selected.status === "resolved" ? <button className="outline-button" disabled={busy} onClick={() => mark("open")}><RotateCcw size={14} /> Reopen</button> : <button className="primary-button" disabled={busy} onClick={() => mark("resolved")}><ClipboardCheck size={14} /> Resolve review</button>}
          </div>
        </Panel>
      </div>}
    </div>}
  </div>;
}