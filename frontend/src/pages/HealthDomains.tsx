import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Activity, Bone, Eye, HeartPulse, Moon, Radio, ShieldCheck, Utensils, Dumbbell, Droplets } from "lucide-react";
import { Link } from "react-router-dom";
import { DataNotice, EmptyState, PageTitle, Panel } from "../components/Ui";
import { getHealthDomains } from "../services/monitoringService";
import { listAstronauts } from "../services/astronautService";
import { ApiError, CrewPicker, StateBadge } from "./HealthCommon";
import { useCrewSelection } from "../state/CrewSelection";

const icons: Record<string, typeof Activity> = { cardiovascular: HeartPulse, bone: Bone, radiation: Radio, muscle_fitness: Dumbbell, vision_neuro: Eye, immune: ShieldCheck, sleep_behavioral: Moon, nutrition_renal: Utensils };
const paths: Record<string, string> = { bone: "/bone-health", radiation: "/radiation" };

export default function HealthDomains() {
  const { activeAstronautId, setActiveAstronautId } = useCrewSelection();
  const crew = useQuery({ queryKey: ["crew"], queryFn: () => listAstronauts() });
  const astronautId = activeAstronautId || crew.data?.[0]?.id || "";
  const domains = useQuery({ queryKey: ["health-domains", astronautId], queryFn: () => getHealthDomains(astronautId), enabled: !!astronautId });
  const records = domains.data || [];
  const available = records.filter((domain) => domain.status === "data_available").length;
  return <div className="page-stack">
    <PageTitle eyebrow="INDIVIDUAL HEALTH COVERAGE" title="Health domains" subtitle="See which systems have source records and where the monitoring gaps remain." action={crew.data?.length ? <CrewPicker crew={crew.data} value={astronautId} onChange={setActiveAstronautId} /> : undefined} />
    <DataNotice />
    <div className="domain-hero"><div className="domain-ring"><strong>{available}<small>/{records.length || 8}</small></strong><span>domains with<br />available data</span></div><div><span className="eyebrow">COVERAGE CHECK</span><h2>Evidence first, one domain at a time</h2><p>Each status reflects recorded source data. An unmonitored domain is not treated as healthy, and missing records do not receive an estimated score.</p></div></div>
    <div className="domain-grid">{records.map((domain) => { const Icon = icons[domain.key] || Activity; const path = paths[domain.key]; return <article className={`domain-card domain-${domain.status}`} key={domain.key}><div className="domain-card-top"><div className="domain-icon"><Icon size={17} /></div><StateBadge status={domain.status} /></div><h3>{domain.label}</h3><p>{domain.detail}</p><div className="domain-card-foot"><span>{domain.record_count} source record{domain.record_count === 1 ? "" : "s"}</span>{path && <Link to={`${path}?astronaut=${astronautId}`}>Open module <ArrowUpRight size={12} /></Link>}</div></article>; })}</div>
    <div className="dashboard-grid two-equal"><Panel title="Active monitoring" detail="Signals currently collected by AstroGuard"><div className="coverage-notes"><div><HeartPulse size={15} /><span><strong>Cardiovascular</strong><small>Heart rate and blood pressure observations</small></span><StateBadge status={records.find((item) => item.key === "cardiovascular")?.status || "insufficient"} /></div><div><Bone size={15} /><span><strong>Bone health</strong><small>Manual source entries for imaging, markers, exercise, nutrition</small></span><Link to={`/bone-health?astronaut=${astronautId}`}>Open</Link></div><div><Radio size={15} /><span><strong>Radiation</strong><small>Dosimeter records with quantity-specific units</small></span><Link to={`/radiation?astronaut=${astronautId}`}>Open</Link></div></div></Panel><Panel title="Not connected yet" detail="These fields remain visible so missing coverage is clear"><div className="coverage-notes"><div><Eye size={15} /><span><strong>Vision & neuro</strong><small>No observations have been recorded</small></span><StateBadge status="not_monitored" /></div><div><Droplets size={15} /><span><strong>Immune, sleep, nutrition & renal</strong><small>Dedicated capture workflows are not connected yet</small></span><StateBadge status="not_monitored" /></div></div><div className="insight-callout"><Activity size={14} /><span>Sensor integrations and validated domain models are future work; AstroGuard does not fill gaps with generated data.</span></div></Panel></div>
    {domains.error && <ApiError error={domains.error} />}
    {!crew.isLoading && !crew.data?.length && <EmptyState title="No crew profile found" detail="Create a crew profile to inspect domain coverage." />}
  </div>;
}
