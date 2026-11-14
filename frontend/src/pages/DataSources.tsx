import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, Database, ExternalLink, FileCheck2, FlaskConical, Radio, Search } from "lucide-react";
import { getDataSources } from "../services/dataService";
import { DataNotice, ErrorState, LoadingState, PageTitle, Panel, StatusPill } from "../components/Ui";
import { nasaCatalog } from "../data/nasaCatalog";

export default function DataSources() {
  const query = useQuery({ queryKey: ["data-sources"], queryFn: getDataSources });
  const [search, setSearch] = useState("");
  const [group, setGroup] = useState("All sources");
  const groups = ["All sources", "Frameworks", "Human studies", "OSDR studies", "Tools & APIs"];
  const entries = useMemo(() => nasaCatalog.filter((item) => {
    const matchesGroup = group === "All sources" || item.group === group;
    const text = `${item.title} ${item.summary} ${item.astroguardUse} ${item.id}`.toLowerCase();
    return matchesGroup && text.includes(search.trim().toLowerCase());
  }), [group, search]);
  if (query.isLoading) return <LoadingState />;
  if (query.error) return <ErrorState message={(query.error as Error).message} onRetry={() => query.refetch()} />;
  return <div className="page-stack">
    <PageTitle eyebrow="PROVENANCE & CONFIGURATION" title="Data sources" subtitle="Source labels follow every measurement and analysis record" />
    <DataNotice />
    <Panel title="NASA research catalog" detail="Research frameworks, study records, repositories, and tools from the NASA references you shared">
      <div className="nasa-catalog-intro"><BookOpen size={18} /><p>Browse the NASA sources connected to AstroGuard's health domains. “Cataloged · not imported” means we have identified the study, but its data files are not part of astronaut records.</p></div>
      <div className="nasa-catalog-controls">
        <label className="nasa-catalog-search"><Search size={14} /><input aria-label="Search NASA sources" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search NASA sources, risks, study IDs…" /></label>
        <span className="nasa-result-count">{entries.length} of {nasaCatalog.length} sources</span>
      </div>
      <div className="nasa-filter-row" aria-label="Filter NASA sources by category">
        {groups.map((item) => <button key={item} type="button" className={group === item ? "nasa-filter active" : "nasa-filter"} onClick={() => setGroup(item)}>{item}</button>)}
      </div>
      <div className="nasa-catalog-grid">
        {entries.map((item) => <article className="nasa-source-card" key={item.id}>
          <div className="nasa-source-top"><span className="nasa-source-icon">{item.group === "OSDR studies" || item.group === "Human studies" ? <FlaskConical size={15} /> : item.group === "Tools & APIs" ? <Radio size={15} /> : <BookOpen size={15} />}</span><span className={`nasa-status nasa-status-${item.status === "Live API" ? "live" : item.status === "Reference" ? "reference" : item.status === "Portal / request" ? "request" : "cataloged"}`}>{item.status}</span></div>
          <div className="nasa-source-group">{item.group}</div>
          <h3>{item.title}</h3>
          <p>{item.summary}</p>
          <div className="nasa-use"><strong>AstroGuard use</strong><span>{item.astroguardUse}</span></div>
          <a className="source-link" href={item.url} target="_blank" rel="noreferrer">Open NASA source <ExternalLink size={13} /></a>
        </article>)}
        {!entries.length && <div className="nasa-empty"><Database size={18} /><strong>No matching NASA source</strong><span>Try a dataset ID, study name, or another category.</span></div>}
      </div>
    </Panel>
    <div className="source-grid">{query.data?.map((source) => <Panel title={source.name} detail={source.organization} key={source.id} className="source-card">
      <div className="source-card-icon">{source.is_simulated ? <Radio size={19} /> : <Database size={19} />}</div>
      <p>{source.description}</p>
      <div className="source-meta"><span>Dataset version</span><strong>{source.dataset_version || "Not specified"}</strong></div>
      <div className="source-meta"><span>Connection</span><StatusPill status={source.status} /></div>
      <div className="source-meta"><span>Data class</span><strong>{source.is_simulated ? "Synthetic demo" : "External source"}</strong></div>
      {source.url && <a className="source-link" href={source.url} target="_blank" rel="noreferrer">Source information <ExternalLink size={13} /></a>}
    </Panel>)}</div>
    <Panel title="NASA data integration" detail="RadLab API feed · study imports remain source-linked">
      <div className="integration-note"><FileCheck2 size={19} /><div><strong>RadLab's ISS radiation feed is now connected as environmental context.</strong><p>The live feed is shown in Radiation Monitoring and kept separate from astronaut dosimeter records. Other OSDR, NLSP, and study entries above remain catalog references until a specific export is reviewed and imported with its provenance.</p></div></div>
    </Panel>
  </div>;
}
