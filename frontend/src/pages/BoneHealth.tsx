import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Bone, ClipboardPlus, Info, ScanLine } from "lucide-react";
import { Link } from "react-router-dom";
import { DataNotice, EmptyState, PageTitle, Panel, formatStamp } from "../components/Ui";
import { createBoneAssessment, getBoneAssessments, getHealthDomains } from "../services/monitoringService";
import { listAstronauts } from "../services/astronautService";
import type { BoneAssessment } from "../types";
import { ApiError, CrewPicker, StateBadge } from "./HealthCommon";
import { useCrewSelection } from "../state/CrewSelection";

const typeLabels: Record<BoneAssessment["assessment_type"], string> = { scan: "Imaging / scan", turnover_marker: "Bone turnover marker", exercise: "Exercise record", nutrition: "Nutrition record" };

export default function BoneHealth() {
  const queryClient = useQueryClient();
  const { activeAstronautId, setActiveAstronautId } = useCrewSelection();
  const [assessmentType, setAssessmentType] = useState<BoneAssessment["assessment_type"]>("scan");
  const [metric, setMetric] = useState("");
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState("");
  const [source, setSource] = useState("");
  const [recordedAt, setRecordedAt] = useState("");
  const [sourceVerified, setSourceVerified] = useState(false);
  const [notes, setNotes] = useState("");
  const crew = useQuery({ queryKey: ["crew"], queryFn: () => listAstronauts() });
  const astronautId = activeAstronautId || crew.data?.[0]?.id || "";
  const records = useQuery({ queryKey: ["bone-health", astronautId], queryFn: () => getBoneAssessments(astronautId), enabled: !!astronautId });
  const domains = useQuery({ queryKey: ["health-domains", astronautId], queryFn: () => getHealthDomains(astronautId), enabled: !!astronautId });
  const save = useMutation({
    mutationFn: () => createBoneAssessment(astronautId, { assessment_type: assessmentType, metric: metric.trim(), value: Number(value), unit: unit.trim(), source: source.trim(), source_verified: sourceVerified, notes: notes.trim(), recorded_at: recordedAt ? new Date(recordedAt).toISOString() : undefined }),
    onSuccess: async () => { setMetric(""); setValue(""); setUnit(""); setNotes(""); await Promise.all([queryClient.invalidateQueries({ queryKey: ["bone-health", astronautId] }), queryClient.invalidateQueries({ queryKey: ["health-domains", astronautId] })]); },
  });
  if (crew.isLoading) return <div className="page-stack"><PageTitle title="Bone health" /><div className="state-box">Loading crew records…</div></div>;
  const list = records.data || [];
  const domainState = domains.data?.find((item) => item.key === "bone")?.status || "insufficient";
  return <div className="page-stack">
    <PageTitle eyebrow="LONG-DURATION HEALTH" title="Bone health record" subtitle="Keep scans, turnover markers, exercise, and nutrition records together with their source." action={<CrewPicker crew={crew.data || []} value={astronautId} onChange={setActiveAstronautId} />} />
    <DataNotice />
    <div className="bone-hero"><div className="bone-hero-icon"><Bone size={25} /></div><div className="bone-hero-copy"><span>INDIVIDUAL RECORD</span><h2>{list.length ? `${list.length} source record${list.length === 1 ? "" : "s"}` : "No bone measurements recorded"}</h2><p>{list.length ? "Review source, unit, and verification for every observation." : "No BMD, BMC, scan, or turnover data is available for this crew member yet."}</p></div><StateBadge status={domainState} /></div>
    <div className="dashboard-grid two-equal bone-grid">
      <Panel title="Add a source record" detail="Enter the reported value and unit as documented; AstroGuard does not estimate bone loss." action={<ClipboardPlus size={15} color="#61bc91" />}>
        <form className="checkin-form" onSubmit={(event: FormEvent) => { event.preventDefault(); save.mutate(); }}>
          <label className="form-label">Record type<select value={assessmentType} onChange={(event) => setAssessmentType(event.target.value as BoneAssessment["assessment_type"])}><option value="scan">Imaging / scan</option><option value="turnover_marker">Bone turnover marker</option><option value="exercise">Exercise record</option><option value="nutrition">Nutrition record</option></select></label>
          <div className="measurement-input-grid"><label className="form-label">Measure or metric<input required value={metric} onChange={(event) => setMetric(event.target.value)} placeholder="e.g. BMD at lumbar spine" /></label><label className="form-label">Reported value<div className="value-unit-row"><input required type="number" step="any" value={value} onChange={(event) => setValue(event.target.value)} /><input required value={unit} onChange={(event) => setUnit(event.target.value)} placeholder="Unit" aria-label="Reported unit" /></div></label></div>
          <label className="form-label">Source or instrument<input required value={source} onChange={(event) => setSource(event.target.value)} placeholder="e.g. DXA report, device ID, lab" /></label>
          <label className="form-label">Record date & time <span className="optional">Optional · defaults to now</span><input type="datetime-local" value={recordedAt} onChange={(event) => setRecordedAt(event.target.value)} /></label>
          <label className="form-label">Notes <span className="optional">Optional</span><textarea rows={2} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Site, method, context, or source details" /></label>
          <label className="checkbox-row"><input type="checkbox" checked={sourceVerified} onChange={(event) => setSourceVerified(event.target.checked)} /><span>I checked this entry against its stated source</span></label>
          <button className="primary-button" disabled={save.isPending || !metric.trim() || !unit.trim() || !source.trim()}>{save.isPending ? "Saving record…" : "Save bone health record"}</button>
          <ApiError error={save.error} />
        </form>
      </Panel>
      <div className="bone-side-stack">
        <Panel title="How this record is used" detail="Observed values only">
          <div className="bone-use-list"><div><ScanLine size={15} /><span><strong>Imaging</strong><small>DXA, ultrasound, BMD, or BMC source records</small></span></div><div><Info size={15} /><span><strong>Markers & context</strong><small>Turnover, exercise, and nutrition notes are stored as entered</small></span></div></div>
          <div className="insight-callout bone-note"><Info size={14} /><span>Routine vital signs and a 14-day learning window do not estimate bone loss. Population averages are not used as an individual prediction.</span></div>
          <div className="panel-foot"><Link to={`/health-domains?astronaut=${astronautId}`}>View domain availability <ArrowUpRight size={13} /></Link></div>
        </Panel>
        <Panel title="Latest entry" detail="Most recent record with source provenance">
          {list[0] ? <div className="bone-latest"><div className="bone-latest-symbol"><Bone size={17} /></div><div><strong>{list[0].metric}</strong><p>{list[0].value} {list[0].unit} · {typeLabels[list[0].assessment_type]}</p><small>{formatStamp(list[0].recorded_at)} · {list[0].source}</small></div><StateBadge status={list[0].source_verified ? "verified" : "awaiting_medical_review"} /></div> : <EmptyState title="Awaiting source records" detail="Add a report or measurement when one is available." />}
        </Panel>
      </div>
    </div>
    <Panel title="Bone health history" detail="Newest entries first · values stay attached to their reported units">
      {records.isLoading ? <div className="state-box">Loading bone records…</div> : list.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>Record</th><th>Value</th><th>Source</th><th>Recorded</th><th>Source check</th></tr></thead><tbody>{list.map((item) => <tr key={item.id}><td><strong>{item.metric}</strong><small className="table-secondary">{typeLabels[item.assessment_type]}</small></td><td className="reading-cell">{item.value} <small>{item.unit}</small></td><td>{item.source}</td><td className="muted-text">{formatStamp(item.recorded_at)}</td><td><StateBadge status={item.source_verified ? "verified" : "awaiting_medical_review"} /></td></tr>)}</tbody></table></div> : <EmptyState title="No bone history yet" detail="Records appear here when a source measurement is entered." />}
    </Panel>
  </div>;
}
