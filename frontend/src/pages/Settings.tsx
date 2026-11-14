import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Database, KeyRound, RefreshCw, Server } from "lucide-react";
import { getApiHealth } from "../services/dataService";
import { DataNotice, ErrorState, LoadingState, PageTitle, Panel, StatusPill } from "../components/Ui";

export default function Settings() {
  const health = useQuery({ queryKey: ["api-health"], queryFn: getApiHealth, refetchInterval: 30000 });
  if (health.isLoading) return <LoadingState label="Checking service configuration" />;
  return <div className="page-stack">
    <PageTitle eyebrow="APPLICATION CONFIGURATION" title="Settings" subtitle="Local prototype service and research status" action={<button className="outline-button" onClick={() => health.refetch()}><RefreshCw size={14} /> Refresh status</button>} />
    <DataNotice />
    {health.error && <ErrorState message={(health.error as Error).message} onRetry={() => health.refetch()} />}
    <div className="dashboard-grid two-equal">
      <Panel title="Service status" detail="Current local development connection">
        <div className="settings-row"><div className="settings-icon"><Server size={16} /></div><div><strong>FastAPI backend</strong><span>http://localhost:8000</span></div><StatusPill status={health.data?.status || "offline"} /></div>
        <div className="settings-row"><div className="settings-icon"><Database size={16} /></div><div><strong>Database</strong><span>Uses DATABASE_URL; SQLite demo default</span></div><StatusPill status={health.data?.database || "unknown"} /></div>
        <div className="settings-row"><div className="settings-icon"><CheckCircle2 size={16} /></div><div><strong>Seed data</strong><span>Generated once when database is empty</span></div><StatusPill status="synthetic demo" /></div>
      </Panel>
      <Panel title="Prototype safeguards" detail="Deployment requirements">
        <div className="safeguard-list"><div><KeyRound size={16} /><span><strong>No authentication configured</strong><small>Use only with local synthetic data; add identity and role-based access before any real health records.</small></span></div><div><Database size={16} /><span><strong>Set a managed PostgreSQL URL</strong><small>For shared environments, configure DATABASE_URL and run the Alembic migration.</small></span></div><div><CheckCircle2 size={16} /><span><strong>Model is experimental</strong><small>Baseline flags are not validated and must be reviewed by qualified medical personnel.</small></span></div></div>
      </Panel>
    </div>
  </div>;
}