import { Activity, CircleAlert, Info } from "lucide-react";
import type { ReactNode } from "react";

export function PageTitle({ eyebrow, title, subtitle, action }: { eyebrow?: string; title: string; subtitle?: string; action?: ReactNode }) {
  return <div className="page-title"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{action && <div className="page-action">{action}</div>}</div>;
}
export function Panel({ title, detail, action, children, className = "" }: { title: string; detail?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={"panel " + className}><div className="panel-head"><div><h2>{title}</h2>{detail && <p>{detail}</p>}</div>{action}</div>{children}</section>;
}
export function Avatar({ name, color = "#198D6D", size = "md" }: { name: string; color?: string; size?: "sm" | "md" | "lg" }) {
  return <div className={"avatar avatar-" + size} style={{ backgroundColor: color }}>{name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase()}</div>;
}
export function StatusPill({ status }: { status: string }) {
  const label = status.replace("_", " ");
  return <span className={"status-pill status-" + status.toLowerCase().replace(/\s+/g, "-")}>{label}</span>;
}
export function StatCard({ label, value, trend, tone = "green", icon }: { label: string; value: string | number; trend?: string; tone?: string; icon?: ReactNode }) {
  return <div className={"stat-card tone-" + tone}><div className="stat-top"><span>{label}</span><span className="stat-icon">{icon || <Activity size={15} />}</span></div><div className="stat-value">{value}</div>{trend && <div className="stat-trend"><span className="trend-dot" />{trend}</div>}</div>;
}
export function DataNotice({ compact = false }: { compact?: boolean }) {
  return <div className={"data-notice " + (compact ? "compact" : "")}><Info size={14} /><span>Research prototype · demo readings are synthetic and not NASA observations. Flags are prompts for human review, not diagnoses.</span></div>;
}
export function LoadingState({ label = "Loading mission data" }: { label?: string }) {
  return <div className="state-box"><span className="spinner" /><span>{label}</span></div>;
}
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="state-box error-state"><CircleAlert size={17} /><span>{message}</span>{onRetry && <button className="text-button" onClick={onRetry}>Retry</button>}</div>;
}
export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="empty-state"><div className="empty-icon"><Activity size={18} /></div><strong>{title}</strong><p>{detail}</p></div>;
}
export function formatStamp(value: string, withTime = true) {
  const date = parseStamp(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return new Intl.DateTimeFormat(undefined, withTime ? { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" } : { month: "short", day: "numeric", year: "numeric" }).format(date);
}
export function parseStamp(value: string) {
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}
export function prettyMetric(metric: string) {
  const names: Record<string, string> = { heart_rate: "Heart rate", spo2: "Blood oxygen", temperature: "Body temperature", systolic_bp: "Systolic pressure", diastolic_bp: "Diastolic pressure" };
  return names[metric] || metric.replace(/_/g, " ");
}
