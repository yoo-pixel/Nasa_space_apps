import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowUpRight, HeartPulse, Radio, UserRound } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { getMedicalHistory, getAstronaut } from "../services/astronautService";
import { getBaselines, getMeasurements, getAnalyses } from "../services/measurementService";
import { getAlerts } from "../services/alertService";
import { MetricHistoryChart } from "../components/Charts";
import { Avatar, DataNotice, EmptyState, ErrorState, formatStamp, LoadingState, PageTitle, Panel, parseStamp, prettyMetric, StatusPill } from "../components/Ui";
import { StateBadge } from "./HealthCommon";
import { useCrewSelection } from "../state/CrewSelection";

const metricKeys = ["heart_rate", "spo2", "temperature", "systolic_bp", "diastolic_bp"];
export default function Profile() {
  const { id = "" } = useParams();
  const { setActiveAstronautId } = useCrewSelection();
  const [metric, setMetric] = useState("heart_rate");
  useEffect(() => { if (id) setActiveAstronautId(id); }, [id, setActiveAstronautId]);
  const astronaut = useQuery({ queryKey: ["astronaut", id], queryFn: () => getAstronaut(id) });
  const readings = useQuery({ queryKey: ["measurements", id], queryFn: () => getMeasurements(id) });
  const history = useQuery({ queryKey: ["history", id], queryFn: () => getMedicalHistory(id) });
  const baselines = useQuery({ queryKey: ["baselines", id], queryFn: () => getBaselines(id) });
  const alerts = useQuery({ queryKey: ["alerts", id], queryFn: () => getAlerts() });
  const analyses = useQuery({ queryKey: ["analyses", id], queryFn: () => getAnalyses(id) });
  const currentBaseline = baselines.data?.find((item) => item.metric === metric);
  const chart = useMemo(() => (readings.data || []).filter((r) => r.metric === metric).slice().reverse().map((r) => ({ date: parseStamp(r.measured_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }), value: r.value })), [readings.data, metric]);
  if (astronaut.isLoading) return <LoadingState label="Loading astronaut profile" />;
  if (astronaut.error || !astronaut.data) return <ErrorState message={(astronaut.error as Error)?.message || "Profile not found"} />;
  const person = astronaut.data;
  const personAlerts = alerts.data?.filter((a) => a.astronaut_id === id) || [];
  return <div className="page-stack">
    <Link to="/crew" className="back-link"><ArrowLeft size={14} /> Crew roster</Link>
    <PageTitle eyebrow={person.mission.name + " · " + person.role} title={person.full_name} subtitle={"Callsign " + person.callsign + " · " + person.nationality} action={<Link className="primary-button" to={"/check-in?astronaut=" + id}><HeartPulse size={14} /> New check-in</Link>} />
    <DataNotice />
    <div className="profile-banner"><Avatar name={person.full_name} color={person.avatar_color} size="lg" /><div className="profile-identity"><div><strong>{person.callsign}</strong><StatusPill status={person.monitoring_status} /></div><span>{person.role} · {person.mission.name} · {person.mission.destination}</span></div><div className="profile-last"><Radio size={14} /> Monitoring profile active</div></div>
    <div className="dashboard-grid two-equal">
      <Panel title="Current indicators" detail="Latest available measurements">
        <div className="vital-grid">{metricKeys.map((key) => {
          const reading = readings.data?.find((r) => r.metric === key);
          const baseline = baselines.data?.find((b) => b.metric === key);
          return <button className={"vital-card " + (metric === key ? "selected" : "")} key={key} onClick={() => setMetric(key)}><span>{prettyMetric(key)}</span><strong>{reading ? reading.value : "—"} <small>{reading?.unit || baseline?.unit}</small></strong><em>{baseline ? "Personal median " + baseline.median : "Baseline forming"}</em></button>;
        })}</div>
      </Panel>
      <Panel title="Recent analysis" detail="Experimental statistical findings" action={<Link className="inline-link" to={"/analytics?astronaut=" + id}>Analytics <ArrowUpRight size={13} /></Link>}>
        {analyses.data?.[0] ? <div className="analysis-result"><div className="analysis-score"><span>{Math.round((analyses.data[0].anomaly_score || 0) * 100)}</span><small>band delta</small></div><div><strong>{analyses.data[0].summary}</strong><p>{formatStamp(analyses.data[0].created_at)} · {analyses.data[0].model_name} v{analyses.data[0].model_version}</p><span className="source-badge">{analyses.data[0].needs_review ? "Human review suggested" : "No flagged deviations"}</span></div></div> : <EmptyState title="No analysis run yet" detail="A new health check-in will create an analysis record." />}
      </Panel>
    </div>
    <Panel title={prettyMetric(metric) + " history"} detail="Select another indicator above · shaded band shows personal demo range" action={currentBaseline && <span className="baseline-chip">{currentBaseline.lower_bound}–{currentBaseline.upper_bound} {currentBaseline.unit}</span>}>
      {chart.length ? <div className="profile-chart"><MetricHistoryChart data={chart} unit={currentBaseline?.unit || ""} bounds={currentBaseline ? { low: currentBaseline.lower_bound, high: currentBaseline.upper_bound, median: currentBaseline.median } : undefined} /></div> : <EmptyState title="No history available" detail="Measurements will appear here after check-ins are recorded." />}
    </Panel>
    <div className="dashboard-grid two-equal">
      <Panel title="Medical history" detail="Source and review status for stored profile notes" action={<Link className="inline-link" to={`/personalized-learning?astronaut=${id}`}>Review history <ArrowUpRight size={13} /></Link>}>
        {history.data?.length ? <div className="history-list">{history.data.map((item) => <div className="history-item" key={item.id}><div className="history-icon"><UserRound size={15} /></div><div><div className="history-review-title"><strong>{item.category}</strong><StateBadge status={item.verification_status} /></div><p>{item.summary}</p><span>{formatStamp(item.recorded_at, false)} · {item.recorded_by} · Source: {item.source}</span></div></div>)}</div> : <EmptyState title="No medical history recorded" detail="No history records are attached to this demo profile." />}
      </Panel>
      <Panel title="Related alerts" detail="Open or resolved flags for this astronaut" action={<Link className="inline-link" to="/alerts">All alerts <ArrowUpRight size={13} /></Link>}>
        {personAlerts.length ? <div className="profile-alert-list">{personAlerts.slice(0, 5).map((alert) => <Link to={"/review?id=" + alert.id} key={alert.id}><span><strong>{alert.title}</strong><small>{formatStamp(alert.created_at)}</small></span><StatusPill status={alert.status} /></Link>)}</div> : <EmptyState title="No alerts" detail="No flags are associated with this profile." />}
      </Panel>
    </div>
  </div>;
}
