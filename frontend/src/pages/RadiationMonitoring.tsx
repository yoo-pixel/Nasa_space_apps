import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Radio, Shield, Waves } from "lucide-react";
import { DataNotice, EmptyState, PageTitle, Panel, formatStamp } from "../components/Ui";
import { createRadiationRecord, getHealthDomains, getRadiationRecords } from "../services/monitoringService";
import { listAstronauts } from "../services/astronautService";
import type { RadiationRecord } from "../types";
import { ApiError, CrewPicker, StateBadge } from "./HealthCommon";
import { useCrewSelection } from "../state/CrewSelection";
import RadLabExplorer from "./RadLabExplorer";

const unitOptions: Record<RadiationRecord["exposure_type"], string[]> = {
  absorbed: ["Gy", "mGy", "µGy", "uGy"],
  equivalent: ["Sv", "mSv", "µSv", "uSv"],
  effective: ["Sv", "mSv", "µSv", "uSv"],
  dose_rate: ["Gy/h", "mGy/h", "µGy/h", "uGy/h", "Sv/h", "mSv/h", "µSv/h", "uSv/h"],
};
const exposureLabels: Record<RadiationRecord["exposure_type"], string> = { absorbed: "Absorbed dose", equivalent: "Equivalent dose", effective: "Effective dose", dose_rate: "Dose rate" };

export default function RadiationMonitoring() {
  const queryClient = useQueryClient();
  const { activeAstronautId, setActiveAstronautId } = useCrewSelection();
  const [dosimeter, setDosimeter] = useState("");
  const [exposureType, setExposureType] = useState<RadiationRecord["exposure_type"]>("effective");
  const [basis, setBasis] = useState<RadiationRecord["measurement_basis"]>("interval");
  const [unit, setUnit] = useState("mSv");
  const [value, setValue] = useState("");
  const [source, setSource] = useState("");
  const [measuredAt, setMeasuredAt] = useState("");
  const [phase, setPhase] = useState("");
  const [event, setEvent] = useState("");
  const [shielding, setShielding] = useState("");
  const [notes, setNotes] = useState("");
  const [sourceVerified, setSourceVerified] = useState(false);
  const [filter, setFilter] = useState("all");
  const crew = useQuery({ queryKey: ["crew"], queryFn: () => listAstronauts() });
  const astronautId = activeAstronautId || crew.data?.[0]?.id || "";
  const records = useQuery({ queryKey: ["radiation", astronautId], queryFn: () => getRadiationRecords(astronautId), enabled: !!astronautId });
  const domains = useQuery({ queryKey: ["health-domains", astronautId], queryFn: () => getHealthDomains(astronautId), enabled: !!astronautId });
  const save = useMutation({
    mutationFn: () => createRadiationRecord(astronautId, { dosimeter_id: dosimeter.trim(), exposure_type: exposureType, measurement_basis: exposureType === "dose_rate" ? "rate" : basis, value: Number(value), unit: unitOptions[exposureType].includes(unit) ? unit : unitOptions[exposureType][0], source: source.trim(), mission_phase: phase.trim(), event: event.trim(), shielding: shielding.trim(), source_verified: sourceVerified, notes: notes.trim(), measured_at: measuredAt ? new Date(measuredAt).toISOString() : undefined }),
    onSuccess: async () => { setValue(""); setNotes(""); await Promise.all([queryClient.invalidateQueries({ queryKey: ["radiation", astronautId] }), queryClient.invalidateQueries({ queryKey: ["health-domains", astronautId] })]); },
  });
  const rows = records.data || [];
  const filtered = useMemo(() => filter === "all" ? rows : rows.filter((record) => record.exposure_type === filter), [rows, filter]);
  const latestVerified = rows.find((row) => row.source_verified);
  if (crew.isLoading) return <div className="page-stack"><PageTitle title="Radiation monitoring" /><div className="state-box">Loading crew records…</div></div>;
  return <div className="page-stack">
    <PageTitle eyebrow="ENVIRONMENTAL EXPOSURE" title="Radiation monitoring" subtitle="Capture dosimeter readings with units, time, mission phase, and shielding context." action={<CrewPicker crew={crew.data || []} value={astronautId} onChange={setActiveAstronautId} />} />
    <DataNotice />
    <div className="radiation-summary-grid"><div className="radiation-summary-card"><div className="summary-icon"><Radio size={16} /></div><span>Source records</span><strong>{rows.length}</strong><small>for this crew member</small></div><div className="radiation-summary-card"><div className="summary-icon purple"><Waves size={16} /></div><span>Latest source-checked</span><strong>{latestVerified ? `${latestVerified.value} ${latestVerified.unit}` : "—"}</strong><small>{latestVerified ? `${latestVerified.measurement_basis} · ${formatStamp(latestVerified.measured_at)}` : "No verified reading yet"}</small></div><div className="radiation-summary-card"><div className="summary-icon orange"><Shield size={16} /></div><span>Domain status</span><strong className="summary-status-text">{domains.data?.find((item) => item.key === "radiation")?.status?.replace(/_/g, " ") || "checking"}</strong><small>Source verification is shown per record</small></div></div>
    <div className="dashboard-grid two-equal radiation-grid">
      <Panel title="Record a dosimeter reading" detail="Absorbed dose (Gy) and equivalent/effective dose (Sv) remain separate quantities." action={<Activity size={15} color="#68c798" />}>
        <form className="checkin-form" onSubmit={(event: FormEvent) => { event.preventDefault(); save.mutate(); }}>
          <div className="measurement-input-grid"><label className="form-label">Dosimeter ID<input required value={dosimeter} onChange={(event) => setDosimeter(event.target.value)} placeholder="e.g. AD-042" /></label><label className="form-label">Exposure quantity<select value={exposureType} onChange={(event) => { const next = event.target.value as RadiationRecord["exposure_type"]; setExposureType(next); setUnit(unitOptions[next][0]); setBasis(next === "dose_rate" ? "rate" : "interval"); }}><option value="absorbed">Absorbed dose</option><option value="equivalent">Equivalent dose</option><option value="effective">Effective dose</option><option value="dose_rate">Dose rate</option></select></label></div>
          {exposureType !== "dose_rate" && <label className="form-label">Dose basis<select value={basis} onChange={(event) => setBasis(event.target.value as "interval" | "cumulative")}><option value="interval">Interval dose</option><option value="cumulative">Cumulative dose</option></select></label>}
          <div className="measurement-input-grid"><label className="form-label">Reported value<input required type="number" min="0" step="any" value={value} onChange={(event) => setValue(event.target.value)} /></label><label className="form-label">Unit<select value={unitOptions[exposureType].includes(unit) ? unit : unitOptions[exposureType][0]} onChange={(event) => setUnit(event.target.value)}>{unitOptions[exposureType].map((option) => <option key={option}>{option}</option>)}</select></label></div>
          <label className="form-label">Data source<input required value={source} onChange={(event) => setSource(event.target.value)} placeholder="Device export, dosimetry report, or log" /></label>
          <label className="form-label">Measured at <span className="optional">Optional · defaults to now</span><input type="datetime-local" value={measuredAt} onChange={(event) => setMeasuredAt(event.target.value)} /></label>
          <div className="measurement-input-grid"><label className="form-label">Mission phase<input value={phase} onChange={(event) => setPhase(event.target.value)} placeholder="e.g. transit, EVA, surface" /></label><label className="form-label">Event <span className="optional">Optional</span><input value={event} onChange={(event) => setEvent(event.target.value)} placeholder="e.g. solar event ID" /></label></div>
          <div className="measurement-input-grid"><label className="form-label">Shielding context<input value={shielding} onChange={(event) => setShielding(event.target.value)} placeholder="Configuration or unknown" /></label><label className="form-label">Notes <span className="optional">Optional</span><input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Source context" /></label></div>
          <label className="checkbox-row"><input type="checkbox" checked={sourceVerified} onChange={(event) => setSourceVerified(event.target.checked)} /><span>I checked this entry against its stated source</span></label>
          <button className="primary-button" disabled={save.isPending || !dosimeter.trim() || !source.trim() || !value}>{save.isPending ? "Saving record…" : "Save exposure record"}</button>
          <ApiError error={save.error} />
        </form>
      </Panel>
      <Panel title="Readings stay separate" detail="No ungrounded thresholds, dose conversions, or risk probabilities">
        <div className="radiation-illustration"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="radiation-core"><Radio size={24} /></div><div className="radiation-node node-one" /><div className="radiation-node node-two" /><div className="radiation-node node-three" /></div>
        <div className="radiation-legend"><div><b className="legend-gold" />Gy · absorbed energy per mass</div><div><b className="legend-purple" />Sv · biological weighting quantity</div><div><b className="legend-teal" />Per-hour units · dose rate</div></div>
        <div className="insight-callout"><Shield size={14} /><span>Records are stored as reported. Readings with different units or quantities are not summed into a risk score. Mission thresholds are not configured.</span></div>
      </Panel>
    </div>
    <Panel title="Exposure log" detail="Chronological source records; quantities and units are never combined" action={<label className="filter-control">Filter<select className="subtle-select" value={filter} onChange={(event) => setFilter(event.target.value)}><option value="all">All quantities</option><option value="absorbed">Absorbed dose</option><option value="equivalent">Equivalent dose</option><option value="effective">Effective dose</option><option value="dose_rate">Dose rate</option></select></label>}>
      {records.isLoading ? <div className="state-box">Loading radiation records…</div> : filtered.length ? <div className="table-wrap"><table className="data-table radiation-table"><thead><tr><th>Quantity</th><th>Reading</th><th>Basis</th><th>Dosimeter</th><th>Phase / event</th><th>Shielding</th><th>Source</th><th>Time</th><th>Review</th></tr></thead><tbody>{filtered.map((item) => <tr key={item.id}><td>{exposureLabels[item.exposure_type]}</td><td className="reading-cell">{item.value} <small>{item.unit}</small></td><td>{item.measurement_basis}</td><td>{item.dosimeter_id}</td><td>{[item.mission_phase, item.event].filter(Boolean).join(" · ") || "—"}</td><td>{item.shielding || "—"}</td><td>{item.source}</td><td className="muted-text">{formatStamp(item.measured_at)}</td><td><StateBadge status={item.source_verified ? "verified" : "awaiting_medical_review"} /></td></tr>)}</tbody></table></div> : <EmptyState title="No matching exposure records" detail="Add a dosimeter source record above when a reading is available." />}
    </Panel>
    <RadLabExplorer />
  </div>;
}
