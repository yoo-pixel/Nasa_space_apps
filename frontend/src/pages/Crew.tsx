import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, UserPlus, ArrowUpRight, Filter, Radio } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { createAstronaut, listAstronauts } from "../services/astronautService";
import { getMissions } from "../services/missionService";
import { Avatar, DataNotice, EmptyState, ErrorState, LoadingState, PageTitle, Panel, StatusPill } from "../components/Ui";

export default function Crew() {
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(params.get("q") || "");
  const [status, setStatus] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ full_name: "", callsign: "", role: "Mission specialist", mission_id: "" });
  const [error, setError] = useState("");
  const client = useQueryClient();
  const crew = useQuery({ queryKey: ["crew", search, status], queryFn: () => listAstronauts({ q: search, status }) });
  const missions = useQuery({ queryKey: ["missions"], queryFn: getMissions });
  const searchCrew = (value: string) => { setSearch(value); setParams(value ? { q: value } : {}); };
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); setError("");
    try {
      await createAstronaut({ ...form, mission_id: form.mission_id || missions.data?.[0]?.id, monitoring_status: "stable" });
      setShowForm(false); setForm({ full_name: "", callsign: "", role: "Mission specialist", mission_id: "" });
      await client.invalidateQueries({ queryKey: ["crew"] });
    } catch (e) { setError((e as Error).message); }
  };
  if (crew.isLoading) return <LoadingState label="Loading crew profiles" />;
  if (crew.error) return <ErrorState message={(crew.error as Error).message} onRetry={() => crew.refetch()} />;
  return <div className="page-stack">
    <PageTitle eyebrow="MISSION ROSTER" title="Astronauts" subtitle="Individual crew profiles and monitoring status" action={<button className="primary-button" onClick={() => setShowForm(!showForm)}><UserPlus size={15} /> Add astronaut</button>} />
    <DataNotice compact />
    {showForm && <Panel title="Register crew member" detail="Adds a crew profile to the selected mission">
      <form className="inline-form" onSubmit={save}>
        <label>Full name<input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label>
        <label>Callsign<input required value={form.callsign} onChange={(e) => setForm({ ...form, callsign: e.target.value })} /></label>
        <label>Role<input required value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} /></label>
        <label>Mission<select value={form.mission_id || missions.data?.[0]?.id || ""} onChange={(e) => setForm({ ...form, mission_id: e.target.value })}>{missions.data?.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</select></label>
        <button className="primary-button" type="submit">Save profile</button>{error && <span className="form-error">{error}</span>}
      </form>
    </Panel>}
    <Panel title="Crew roster" detail={(crew.data?.length || 0) + " crew member(s) on active missions"} action={<div className="roster-tools"><div className="field-search"><Search size={14} /><input placeholder="Search name or callsign" value={search} onChange={(e) => searchCrew(e.target.value)} /></div><Filter size={14} /><select className="filter-select" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option><option value="stable">Stable</option><option value="monitoring">Monitoring</option><option value="review">Review</option></select></div>}>
      {crew.data?.length ? <div className="crew-grid">{crew.data.map((person) => <Link className="crew-card" key={person.id} to={"/crew/" + person.id}>
        <div className="crew-card-head"><Avatar name={person.full_name} color={person.avatar_color} size="lg" /><StatusPill status={person.monitoring_status} /></div>
        <div className="crew-name">{person.full_name}</div><div className="crew-callsign">{person.callsign} <span>·</span> {person.role}</div>
        <div className="crew-card-meta"><span><Radio size={13} /> {person.mission.name}</span><span>{person.mission.destination}</span></div>
        <div className="crew-card-foot"><span>Open profile</span><ArrowUpRight size={14} /></div>
      </Link>)}</div> : <EmptyState title="No crew found" detail="Try another search or status filter." />}
    </Panel>
  </div>;
}