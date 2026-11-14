import { useMemo, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Globe2, RefreshCw, Shield } from "lucide-react";
import { RadLabRateChart } from "../components/Charts";
import { Panel } from "../components/Ui";
import { getRadLabFeed } from "../services/dataService";

const initialRange = { start: "2023-01-01T00:00", end: "2023-01-01T01:00", instrument: "DosTel1" };

export default function RadLabExplorer() {
  const [draft, setDraft] = useState(initialRange);
  const [range, setRange] = useState(initialRange);
  const feed = useQuery({
    queryKey: ["nasa-radlab", range.start, range.end, range.instrument],
    queryFn: () => getRadLabFeed(range.start, range.end, range.instrument),
    staleTime: 5 * 60_000,
  });
  const rows = feed.data?.rows || [];
  const stats = useMemo(() => {
    const doseRates = rows.map((row) => row.absorbed_dose_rate).filter((value): value is number => value !== null && Number.isFinite(value));
    const equivalents = rows.map((row) => row.dose_equivalent_rate).filter((value): value is number => value !== null && Number.isFinite(value));
    return {
      average: doseRates.length ? doseRates.reduce((sum, value) => sum + value, 0) / doseRates.length : null,
      equivalentCount: equivalents.length,
    };
  }, [rows]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setRange(draft);
  };

  return <Panel title="ISS environmental telemetry" detail="NASA OSDR RadLab · historical instrument readings" action={<Globe2 size={16} color="#e9ad61" />}>
    <div className="radlab-context"><Shield size={15} /><span>These are spacecraft detector readings. They provide environmental context and do not represent an individual astronaut's personal dose.</span></div>
    <form className="radlab-form" onSubmit={submit}>
      <label className="form-label">Start (UTC)<input type="datetime-local" required value={draft.start} onChange={(event) => setDraft({ ...draft, start: event.target.value })} /></label>
      <label className="form-label">End (UTC)<input type="datetime-local" required value={draft.end} onChange={(event) => setDraft({ ...draft, end: event.target.value })} /></label>
      <label className="form-label">ISS instrument<select value={draft.instrument} onChange={(event) => setDraft({ ...draft, instrument: event.target.value })}><option value="DosTel1">DosTel1</option><option value="REM-Lid">REM-Lid</option><option value="Lidal">Lidal</option></select></label>
      <button className="outline-button radlab-refresh" type="submit" disabled={feed.isFetching}><RefreshCw size={13} />{feed.isFetching ? "Loading NASA data…" : "Refresh NASA data"}</button>
    </form>
    {feed.error && <div className="radlab-error" role="alert">{(feed.error as Error).message}</div>}
    {feed.isLoading ? <div className="state-box">Connecting to NASA RadLab…</div> : feed.data && <>
      <div className="radlab-stat-row">
        <div><span>Telemetry rows</span><strong>{rows.length}</strong><small>{feed.data.instrument} · ISS</small></div>
        <div><span>Average absorbed dose rate</span><strong>{stats.average === null ? "—" : `${stats.average.toFixed(3)} µGy/h`}</strong><small>Only non-null detector values</small></div>
        <div><span>Dose equivalent values</span><strong>{stats.equivalentCount}</strong><small>µSv/h · kept as a separate quantity</small></div>
      </div>
      {rows.length ? <>
        <div className="radlab-chart"><RadLabRateChart data={rows} /></div>
        <div className="radlab-table-heading"><strong>Returned measurements</strong><span>First 10 records · time and units follow NASA's response</span></div>
        <div className="table-wrap"><table className="data-table radlab-table"><thead><tr><th>Timestamp (UTC)</th><th>Instrument</th><th>Absorbed dose rate</th><th>Dose-equivalent rate</th><th>Altitude</th></tr></thead><tbody>{rows.slice(0, 10).map((row, index) => <tr key={`${row.timestamp}-${row.instrument_id}-${index}`}><td>{row.timestamp.replace("T", " ")}</td><td>{row.instrument_id}</td><td>{row.absorbed_dose_rate === null ? "—" : `${row.absorbed_dose_rate.toFixed(3)} µGy/h`}</td><td>{row.dose_equivalent_rate === null ? "—" : `${row.dose_equivalent_rate.toFixed(3)} µSv/h`}</td><td>{row.altitude === null ? "—" : `${row.altitude.toFixed(1)} km`}</td></tr>)}</tbody></table></div>
      </> : <div className="state-box">NASA returned no records for this time window and instrument. Try another period or instrument.</div>}
      {feed.data.truncated && <p className="radlab-footnote">The API response exceeded the display cap; narrow the time window to view all returned rows.</p>}
      <div className="radlab-provenance"><span>Retrieved {new Date(feed.data.retrieved_at).toLocaleString()}</span><a href={feed.data.source_url} target="_blank" rel="noreferrer">Open the matching NASA API query <ExternalLink size={12} /></a></div>
    </>}
  </Panel>;
}
