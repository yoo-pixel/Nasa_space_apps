import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ClipboardPenLine, Info, Plus, Send } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { listAstronauts } from "../services/astronautService";
import { analyzeAstronaut, submitMeasurement } from "../services/measurementService";
import { DataNotice, ErrorState, LoadingState, PageTitle, Panel } from "../components/Ui";
import { useCrewSelection } from "../state/CrewSelection";

const fields = [
  { key: "heart_rate", label: "Heart rate", unit: "bpm", step: "1", min: "20", max: "240" },
  { key: "spo2", label: "Blood oxygen saturation", unit: "%", step: "0.1", min: "50", max: "100" },
  { key: "temperature", label: "Body temperature", unit: "°C", step: "0.1", min: "30", max: "43" },
  { key: "systolic_bp", label: "Systolic blood pressure", unit: "mmHg", step: "1", min: "50", max: "250" },
  { key: "diastolic_bp", label: "Diastolic blood pressure", unit: "mmHg", step: "1", min: "30", max: "150" },
];
export default function Checkin() {
  const crew = useQuery({ queryKey: ["crew"], queryFn: () => listAstronauts() });
  const client = useQueryClient();
  const [params] = useSearchParams();
  const { activeAstronautId, setActiveAstronautId } = useCrewSelection();
  const [values, setValues] = useState<Record<string, string>>({});
  const [symptoms, setSymptoms] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  if (crew.isLoading) return <LoadingState />;
  if (crew.error) return <ErrorState message={(crew.error as Error).message} onRetry={() => crew.refetch()} />;
  const chosen = activeAstronautId || params.get("astronaut") || crew.data?.[0]?.id || "";
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError(""); setSuccess("");
    const entries = fields.filter((field) => values[field.key] !== undefined && values[field.key] !== "");
    if (!chosen) { setError("Select a crew member first."); return; }
    if (!entries.length) { setError("Enter at least one measurement."); return; }
    setBusy(true);
    try {
      const symptomList = symptoms.split(",").map((item) => item.trim()).filter(Boolean);
      await Promise.all(entries.map((field) => submitMeasurement(chosen, {
        metric: field.key, value: Number(values[field.key]), unit: field.unit,
        source_type: "manual", symptoms: symptomList, notes,
      })));
      await analyzeAstronaut(chosen);
      setValues({}); setSymptoms(""); setNotes(""); setSuccess("Check-in saved. Baseline comparison completed; any flags were sent for medical review.");
      await Promise.all([client.invalidateQueries({ queryKey: ["dashboard"] }), client.invalidateQueries({ queryKey: ["monitoring-summary"] }), client.invalidateQueries({ queryKey: ["learning", chosen] }), client.invalidateQueries({ queryKey: ["health-domains", chosen] }), client.invalidateQueries({ queryKey: ["alerts"] }), client.invalidateQueries({ queryKey: ["alert-count"] }), client.invalidateQueries({ queryKey: ["measurements", chosen] })]);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  return <div className="page-stack">
    <PageTitle eyebrow="CREW HEALTH RECORD" title="Health check-in" subtitle="Record one or more available physiological measures" />
    <DataNotice />
    <div className="form-layout">
      <Panel title="New check-in" detail="Manual measurement entry · timestamps are recorded on submission">
        <form className="checkin-form" onSubmit={submit}>
          <label className="form-label">Crew member<select value={chosen} onChange={(e) => setActiveAstronautId(e.target.value)}>{crew.data?.map((person) => <option key={person.id} value={person.id}>{person.callsign} · {person.full_name}</option>)}</select></label>
          <div className="form-section-label"><ClipboardPenLine size={15} /><span>Physiological measurements</span><small>Enter only values collected by your source protocol</small></div>
          <div className="measurement-input-grid">{fields.map((field) => <label className="form-label measurement-input" key={field.key}>{field.label}<div><input type="number" step={field.step} min={field.min} max={field.max} placeholder="—" value={values[field.key] || ""} onChange={(e) => setValues({ ...values, [field.key]: e.target.value })} /><span>{field.unit}</span></div></label>)}</div>
          <label className="form-label">Symptoms or observations <span className="optional">(optional · comma separated)</span><input placeholder="e.g. fatigue, lightheadedness" value={symptoms} onChange={(e) => setSymptoms(e.target.value)} /></label>
          <label className="form-label">Clinical note <span className="optional">(optional)</span><textarea rows={3} placeholder="Context for the medical reviewer..." value={notes} onChange={(e) => setNotes(e.target.value)} /></label>
          {error && <div className="form-alert error">{error}</div>}{success && <div className="form-alert success"><Check size={16} />{success}</div>}
          <div className="form-actions"><span><Info size={14} /> Numeric ranges validate entry format, not clinical safety.</span><button className="primary-button" disabled={busy}>{busy ? "Saving…" : <><Send size={14} /> Save and analyze</>}</button></div>
        </form>
      </Panel>
      <aside className="side-info">
        <div className="side-info-card"><div className="side-info-icon"><Plus size={16} /></div><strong>How this works</strong><p>Each reading is stored in the API with its source marked as manual. The experimental analysis compares it with that astronaut’s personal demo baseline.</p></div>
        <div className="side-info-card"><div className="side-info-icon teal"><Info size={16} /></div><strong>Review remains human</strong><p>Outlying values create review flags. They do not represent diagnoses or automated medical decisions.</p></div>
      </aside>
    </div>
  </div>;
}
