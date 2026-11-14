import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, Download, SlidersHorizontal } from "lucide-react";
import { listAstronauts } from "../services/astronautService";
import { getBaselines, getMeasurements } from "../services/measurementService";
import { MetricHistoryChart } from "../components/Charts";
import { DataNotice, EmptyState, ErrorState, LoadingState, PageTitle, Panel, parseStamp, prettyMetric } from "../components/Ui";
import { useCrewSelection } from "../state/CrewSelection";

const metrics = ["heart_rate", "spo2", "temperature", "systolic_bp", "diastolic_bp"];
export default function Analytics() {
  const crew = useQuery({ queryKey: ["crew"], queryFn: () => listAstronauts() });
  const { activeAstronautId, setActiveAstronautId } = useCrewSelection();
  const [metric, setMetric] = useState("heart_rate");
  const astronautId = activeAstronautId || crew.data?.[0]?.id || "";
  const readings = useQuery({ queryKey: ["measurements", astronautId, metric], queryFn: () => getMeasurements(astronautId, metric), enabled: !!astronautId });
  const baselines = useQuery({ queryKey: ["baselines", astronautId], queryFn: () => getBaselines(astronautId), enabled: !!astronautId });
  const currentBaseline = baselines.data?.find((item) => item.metric === metric);
  const chart = useMemo(() => (readings.data || []).slice().reverse().map((reading) => ({
    date: parseStamp(reading.measured_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    value: reading.value,
  })), [readings.data]);
  if (crew.isLoading) return <LoadingState />;
  if (crew.error) return <ErrorState message={(crew.error as Error).message} />;
  const astronaut = crew.data?.find((person) => person.id === astronautId);
  return <div className="page-stack">
    <PageTitle eyebrow="LONGITUDINAL MONITORING" title="Health analytics" subtitle="Compare measurements with a personal synthetic history baseline" action={<button className="outline-button" onClick={() => window.print()}><Download size={14} /> Export view</button>} />
    <DataNotice />
    <div className="analytics-controls">
      <label><span>Crew member</span><select value={astronautId} onChange={(e) => setActiveAstronautId(e.target.value)}>{crew.data?.map((person) => <option value={person.id} key={person.id}>{person.callsign} · {person.full_name}</option>)}</select></label>
      <label><span>Metric</span><select value={metric} onChange={(e) => setMetric(e.target.value)}>{metrics.map((item) => <option key={item} value={item}>{prettyMetric(item)}</option>)}</select></label>
      <div className="analytics-filter-note"><SlidersHorizontal size={14} /> Showing up to 1,000 recorded values</div>
    </div>
    <Panel title={astronaut ? astronaut.callsign + " · " + prettyMetric(metric) : "Measurement history"} detail="Personal band is descriptive and is not a clinical reference range" action={currentBaseline && <span className="baseline-chip">Median {currentBaseline.median} {currentBaseline.unit}</span>}>
      {readings.isLoading ? <LoadingState /> : readings.error ? <ErrorState message={(readings.error as Error).message} onRetry={() => readings.refetch()} /> : chart.length ? <><div className="analytics-chart"><MetricHistoryChart data={chart} unit={currentBaseline?.unit || ""} bounds={currentBaseline ? { low: currentBaseline.lower_bound, high: currentBaseline.upper_bound, median: currentBaseline.median } : undefined} /></div><div className="chart-legend"><span><i className="legend-dot green" />Recorded values</span><span><i className="legend-band" />Personal demo band</span><span className="chart-count">{chart.length} values · {currentBaseline?.sample_count || 0} baseline samples</span></div></> : <EmptyState title="No measurements yet" detail="Submit a health check-in to begin a measurement history." />}
    </Panel>
    <div className="dashboard-grid two-equal">
      <Panel title="Personal baseline" detail="Calculated from that astronaut’s synthetic history">
        {currentBaseline ? <div className="baseline-details"><div><span>Median</span><strong>{currentBaseline.median} <small>{currentBaseline.unit}</small></strong></div><div><span>Lower band</span><strong>{currentBaseline.lower_bound} <small>{currentBaseline.unit}</small></strong></div><div><span>Upper band</span><strong>{currentBaseline.upper_bound} <small>{currentBaseline.unit}</small></strong></div><div><span>Sample count</span><strong>{currentBaseline.sample_count}</strong></div><p>{currentBaseline.method}</p></div> : <EmptyState title="Baseline unavailable" detail="Additional measurements are needed to form a personal baseline." />}
      </Panel>
      <Panel title="Analysis limits" detail="Experimental statistical comparison">
        <div className="analysis-summary"><div className="analysis-summary-icon"><Activity size={17} /></div><div><strong>Personal median and robust spread</strong><p>Each new check-in is compared against a band derived from recorded history. The demo uses no trained or validated predictive model.</p></div></div>
        <div className="analysis-summary"><div className="analysis-summary-icon muted"><InfoIcon /></div><div><strong>Human interpretation required</strong><p>Differences can reflect context, measurement conditions, or data quality. Review the source reading before any decision.</p></div></div>
      </Panel>
    </div>
  </div>;
}
function InfoIcon() { return <span className="info-glyph">i</span>; }
