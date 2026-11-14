import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, CheckCheck, CircleAlert, Filter, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { getAlerts, updateAlert } from "../services/alertService";
import { listAstronauts } from "../services/astronautService";
import { Avatar, DataNotice, EmptyState, ErrorState, formatStamp, LoadingState, PageTitle, Panel, prettyMetric, StatusPill } from "../components/Ui";

export default function Alerts() {
  const [status, setStatus] = useState("all");
  const client = useQueryClient();
  const alerts = useQuery({ queryKey: ["alerts", status], queryFn: () => getAlerts(status) });
  const crew = useQuery({ queryKey: ["crew"], queryFn: () => listAstronauts() });
  const [busyId, setBusyId] = useState("");
  const update = async (id: string, newStatus: "acknowledged" | "resolved") => {
    setBusyId(id);
    try { await updateAlert(id, { status: newStatus, reviewed_by: "Dr. Rivera" }); await client.invalidateQueries({ queryKey: ["alerts"] }); await client.invalidateQueries({ queryKey: ["alert-count"] }); await client.invalidateQueries({ queryKey: ["dashboard"] }); }
    finally { setBusyId(""); }
  };
  if (alerts.isLoading) return <LoadingState />;
  if (alerts.error) return <ErrorState message={(alerts.error as Error).message} onRetry={() => alerts.refetch()} />;
  return <div className="page-stack">
    <PageTitle eyebrow="SIGNAL MANAGEMENT" title="Alerts" subtitle="Outlying observations for medical personnel to inspect" action={<button className="outline-button" onClick={() => alerts.refetch()}><RefreshCw size={14} /> Refresh</button>} />
    <DataNotice />
    <Panel title="Alert register" detail={(alerts.data?.length || 0) + " alert record(s)"} action={<div className="filter-control"><Filter size={14} /><select value={status} onChange={(e) => setStatus(e.target.value)}><option value="all">All statuses</option><option value="open">Open</option><option value="acknowledged">Acknowledged</option><option value="resolved">Resolved</option></select></div>}>
      {alerts.data?.length ? <div className="table-wrap"><table className="data-table alert-table"><thead><tr><th>Flag</th><th>Crew member</th><th>Observation</th><th>Personal median</th><th>Status</th><th>Detected</th><th>Actions</th></tr></thead><tbody>
        {alerts.data.map((alert) => {
          const person = crew.data?.find((item) => item.id === alert.astronaut_id);
          return <tr key={alert.id}>
            <td><div className="alert-title-cell"><CircleAlert size={15} /><span>{alert.title}</span></div><small>{alert.priority} priority</small></td>
            <td><Link className="crew-cell" to={"/crew/" + alert.astronaut_id}><Avatar name={person?.callsign || "Crew"} color={person?.avatar_color} size="sm" /><strong>{person?.callsign || "Crew"}</strong></Link></td>
            <td className="reading-cell">{prettyMetric(alert.metric)}<br /><strong>{alert.observed_value} <small>{alert.unit}</small></strong></td>
            <td>{alert.baseline_value ?? "—"} <small>{alert.unit}</small></td>
            <td><StatusPill status={alert.status} /></td><td className="muted-text">{formatStamp(alert.created_at)}</td>
            <td><div className="table-actions"><Link className="icon-link" title="Review details" to={"/review?id=" + alert.id}><ArrowUpRight size={15} /></Link>{alert.status === "open" && <button disabled={busyId === alert.id} className="icon-link" title="Acknowledge" onClick={() => update(alert.id, "acknowledged")}><CheckCheck size={15} /></button>}</div></td>
          </tr>;
        })}
      </tbody></table></div> : <EmptyState title="No alerts in this view" detail="The selected status does not have any records." />}
    </Panel>
    <div className="page-footnote"><CircleAlert size={13} /> Alert priority describes review workflow only; it is not a severity grade or diagnosis.</div>
  </div>;
}