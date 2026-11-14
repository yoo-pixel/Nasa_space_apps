import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, ArrowUpRight, BookOpen, Bone, ClipboardList, HeartPulse, MoreHorizontal, Radio, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { getDashboard, getMeasurements } from "../services/measurementService";
import { getAlerts } from "../services/alertService";
import { listAstronauts } from "../services/astronautService";
import { getMonitoringSummary } from "../services/monitoringService";
import { AdmissionsChart, MissionTrendChart, StatusDonut } from "../components/Charts";
import { Avatar, DataNotice, EmptyState, ErrorState, formatStamp, LoadingState, PageTitle, Panel, parseStamp, StatCard, StatusPill, prettyMetric } from "../components/Ui";
import { CrewPicker } from "./HealthCommon";
import { useCrewSelection } from "../state/CrewSelection";

export default function Dashboard() {
  const summary = useQuery({ queryKey: ["dashboard"], queryFn: getDashboard });
  const crew = useQuery({ queryKey: ["crew"], queryFn: () => listAstronauts() });
  const { activeAstronautId, setActiveAstronautId } = useCrewSelection();
  const selectedAstronautId = activeAstronautId || crew.data?.[0]?.id || "";
  const selectedAstronaut = crew.data?.find((person) => person.id === selectedAstronautId);
  const alerts = useQuery({ queryKey: ["alerts"], queryFn: () => getAlerts() });
  const monitoring = useQuery({ queryKey: ["monitoring-summary"], queryFn: getMonitoringSummary });
  const trendReadings = useQuery({ queryKey: ["dashboard-trends", selectedAstronautId], enabled: !!selectedAstronautId, queryFn: () => getMeasurements(selectedAstronautId) });
  const chartData = useMemo(() => {
    const readings = trendReadings.data || [];
    const recentDays = Array.from({ length: 7 }, (_, i) => {
      const d = new Date(); d.setDate(d.getDate() - (6 - i));
      return { day: d.toLocaleDateString(undefined, { month: "short", day: "numeric" }), key: d.toDateString(), heart_rate: 0, spo2: 0, temperature: 0, h: 0, o: 0, t: 0 };
    });
    readings.forEach((item) => {
      const entry = recentDays.find((day) => day.key === parseStamp(item.measured_at).toDateString());
      if (!entry) return;
      if (item.metric === "heart_rate") { entry.heart_rate += item.value; entry.h += 1; }
      if (item.metric === "spo2") { entry.spo2 += item.value; entry.o += 1; }
      if (item.metric === "temperature") { entry.temperature += item.value; entry.t += 1; }
    });
    return recentDays.map((d) => ({ day: d.day, heart_rate: d.h ? +(d.heart_rate / d.h).toFixed(1) : null, spo2: d.o ? +(d.spo2 / d.o).toFixed(1) : null, temperature: d.t ? +(d.temperature / d.t).toFixed(2) : null }));
  }, [trendReadings.data]);
  const weekBars = useMemo(() => {
    const entries = Array.from({ length: 7 }, (_, i) => { const d = new Date(); d.setDate(d.getDate() - (6 - i)); return { day: d.toLocaleDateString(undefined, { weekday: "short" }), key: d.toDateString(), checkins: 0 }; });
    (trendReadings.data || []).forEach((reading) => { const row = entries.find((item) => item.key === parseStamp(reading.measured_at).toDateString()); if (row) row.checkins += 1; });
    return entries;
  }, [trendReadings.data]);
  const statusData = useMemo(() => {
    const all = crew.data || [];
    return [
      { name: "Stable", value: all.filter((a) => a.monitoring_status === "stable").length, color: "#31b98c" },
      { name: "Monitoring", value: all.filter((a) => a.monitoring_status === "monitoring").length, color: "#5f98db" },
      { name: "Review", value: all.filter((a) => a.monitoring_status === "review").length, color: "#dc946d" },
    ].filter((x) => x.value > 0);
  }, [crew.data]);
  if (summary.isLoading) return <LoadingState />;
  if (summary.error) return <ErrorState message={(summary.error as Error).message} onRetry={() => summary.refetch()} />;
  const data = summary.data!;
  const greetingHour = new Date().getHours();
  const greeting = greetingHour < 12 ? "Good morning" : greetingHour < 18 ? "Good afternoon" : "Good evening";
  const missionStart = data.mission_start_date ? parseStamp(data.mission_start_date) : null;
  const missionDay = missionStart && !Number.isNaN(missionStart.getTime()) ? Math.max(1, Math.floor((Date.now() - missionStart.getTime()) / 86400000) + 1) : null;
  const hasTrendData = chartData.some((item) => item.heart_rate !== null || item.spo2 !== null || item.temperature !== null);
  const weekReadingCount = weekBars.reduce((total, item) => total + item.checkins, 0);
  return <div className="page-stack">
    <PageTitle eyebrow={"MISSION OVERVIEW · " + data.mission_name} title={`${greeting}, Dr. Rivera`} subtitle={`${selectedAstronaut ? `${selectedAstronaut.callsign} · ${selectedAstronaut.full_name} · ` : ""}${missionDay ? `mission day ${String(missionDay).padStart(3, "0")}` : "mission start date not set"}`} action={<><CrewPicker crew={crew.data || []} value={selectedAstronautId} onChange={setActiveAstronautId} /><div className="monitoring-live"><span /> LIVE MONITORING</div></>} />
    <DataNotice compact />
    <div className="stats-grid">
      <StatCard label="Astronauts on mission" value={data.astronaut_count.toLocaleString()} trend="All crew profiles current" tone="green" icon={<Users size={16} />} />
      <StatCard label="Measurements recorded" value={data.measurement_count.toLocaleString()} trend="Across 5 physiological indicators" tone="orange" icon={<Activity size={16} />} />
      <StatCard label="Active alerts" value={data.active_alert_count} trend="Requires medical attention" tone="coral" icon={<AlertTriangle size={16} />} />
      <StatCard label="Awaiting review" value={data.review_count} trend="Human assessment required" tone="purple" icon={<ClipboardList size={16} />} />
    </div>
    <Panel title="Long-duration health workflows" detail="Live records across this mission · open a module to review or add source data" action={<Link className="inline-link" to="/health-domains">Coverage map <ArrowUpRight size={13} /></Link>}>
      <div className="monitoring-shortcuts">
        <Link to="/personalized-learning" className="monitoring-shortcut"><span className="shortcut-icon green"><BookOpen size={15} /></span><span><strong>History & learning</strong><small>{monitoring.data?.histories_awaiting_review ?? "—"} history entries awaiting review · {monitoring.data?.sessions_collecting ?? "—"} sessions collecting</small></span><ArrowUpRight size={13} /></Link>
        <Link to="/personalized-learning" className="monitoring-shortcut"><span className="shortcut-icon purple"><HeartPulse size={15} /></span><span><strong>Personal profiles</strong><small>{monitoring.data?.active_profile_count ?? "—"} reviewer-approved profiles · {monitoring.data?.sessions_ready_for_review ?? "—"} ready for review</small></span><ArrowUpRight size={13} /></Link>
        <Link to="/bone-health" className="monitoring-shortcut"><span className="shortcut-icon orange"><Bone size={15} /></span><span><strong>Bone health</strong><small>{monitoring.data?.bone_record_count ?? "—"} source records in the mission log</small></span><ArrowUpRight size={13} /></Link>
        <Link to="/radiation" className="monitoring-shortcut"><span className="shortcut-icon blue"><Radio size={15} /></span><span><strong>Radiation exposure</strong><small>{monitoring.data?.radiation_record_count ?? "—"} dosimeter records in the mission log</small></span><ArrowUpRight size={13} /></Link>
      </div>
    </Panel>
    <div className="dashboard-grid charts-top">
      <Panel title={`${selectedAstronaut?.callsign || "Crew"} health · 7 day trend`} detail="Selected astronaut · recorded readings only · each metric uses its own scale">
        {hasTrendData ? <div className="chart-area trend-chart"><MissionTrendChart data={chartData} /></div> : <EmptyState title="No readings in this period" detail="Actual measurements will appear here after they are recorded." />}
        <div className="chart-legend"><span><i className="legend-dot green" />Heart rate · bpm</span><span><i className="legend-dot purple" />O₂ saturation · %</span><span><i className="legend-dot orange" />Body temp · °C</span></div>
      </Panel>
      <Panel title="Crew status" detail="Current mission cohort" action={<button className="subtle-select">All crew <MoreHorizontal size={14} /></button>}>
        <div className="status-donut-wrap"><div className="donut-chart"><StatusDonut data={statusData} /><div className="donut-center"><strong>{data.astronaut_count}</strong><span>astronauts</span></div></div>
          <div className="donut-legend">{statusData.map((item) => <div key={item.name}><i style={{ background: item.color }} />{item.name}<strong>{item.value}</strong></div>)}</div></div>
        <div className="insight-callout"><Activity size={15} /><span>Baseline comparisons use each astronaut’s synthetic personal history. Outlying values are routed to medical review.</span></div>
      </Panel>
    </div>
    <div className="dashboard-grid charts-bottom">
      <Panel title="Daily health records" detail={`Actual measurement entries · ${selectedAstronaut?.callsign || "selected crew"} · current week`}>
        {trendReadings.isLoading ? <LoadingState label="Loading selected astronaut’s readings" /> : weekReadingCount ? <div className="chart-area admissions-chart"><AdmissionsChart data={weekBars} /></div> : <EmptyState title="No readings this week" detail="Saved measurement records will appear here." />}
        <div className="chart-legend"><span><i className="legend-dot blue" />Recorded readings</span></div>
      </Panel>
      <Panel title="Priority review queue" detail="Flagged by experimental baseline analysis" action={<Link className="inline-link" to="/review">Open queue <ArrowUpRight size={13} /></Link>}>
        <div className="review-list">
          {(data.recent_alerts || []).slice(0, 4).map((alert) => {
            const astronaut = crew.data?.find((item) => item.id === alert.astronaut_id);
            return <Link to={"/review?id=" + alert.id} className="review-row" key={alert.id}>
              <Avatar name={alert.astronaut} color={astronaut?.avatar_color} size="sm" />
              <div className="review-person"><strong>{alert.astronaut}</strong><span>{prettyMetric(alert.metric)}</span></div>
              <div className="review-value"><strong>{alert.observed_value} <small>{alert.unit}</small></strong><span>{formatStamp(alert.created_at)}</span></div>
              <StatusPill status={alert.status} />
            </Link>;
          })}
          {!data.recent_alerts.length && <EmptyState title="Queue is clear" detail="No active flags need review." />}
        </div>
        <div className="panel-foot"><Link to="/alerts">View all alerts <ArrowUpRight size={13} /></Link><span>{alerts.data?.filter((a) => a.status === "open").length || 0} open</span></div>
      </Panel>
    </div>
    <Panel title="Recent health check-ins" detail="Most recently submitted crew measurements" action={<Link className="inline-link" to="/check-in">New check-in <ArrowUpRight size={13} /></Link>}>
      <div className="table-wrap"><table className="data-table"><thead><tr><th>Crew member</th><th>Measurement</th><th>Reading</th><th>Source</th><th>Recorded</th></tr></thead><tbody>
        {data.recent_measurements.map((m) => <tr key={m.id}><td><div className="crew-cell"><Avatar name={m.astronaut} color={crew.data?.find((a) => a.id === m.astronaut_id)?.avatar_color} size="sm" /><strong>{m.astronaut}</strong></div></td><td>{prettyMetric(m.metric)}</td><td className="reading-cell">{m.value} <small>{m.unit}</small></td><td><span className="source-badge">{m.source_type}</span></td><td className="muted-text">{formatStamp(m.measured_at)}</td></tr>)}
      </tbody></table></div>
    </Panel>
    <div className="page-footnote"><HeartPulse size={13} /> AstroGuard is a research prototype and does not provide medical diagnoses.</div>
  </div>;
}
