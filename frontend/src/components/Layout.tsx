import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Activity, Bell, ChevronDown, Database, HeartPulse, LayoutDashboard, Menu, Search,
  Settings, Shield, Stethoscope, Users, X, LineChart, Orbit, Bone, Radio,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getAlerts } from "../services/alertService";
import { getDashboard } from "../services/measurementService";
import { listAstronauts } from "../services/astronautService";
import { Avatar } from "./Ui";
import { useCrewSelection } from "../state/CrewSelection";

const navItems = [
  { label: "Dashboard", to: "/", icon: LayoutDashboard, group: "overview" },
  { label: "Astronauts", to: "/crew", icon: Users, group: "overview" },
  { label: "Health check-in", to: "/check-in", icon: HeartPulse, group: "overview" },
  { label: "Personalized learning", to: "/personalized-learning", icon: Activity, group: "health" },
  { label: "Bone health", to: "/bone-health", icon: Bone, group: "health" },
  { label: "Radiation monitoring", to: "/radiation", icon: Radio, group: "health" },
  { label: "Health domains", to: "/health-domains", icon: Activity, group: "health" },
  { label: "Health analytics", to: "/analytics", icon: LineChart, group: "analytics" },
  { label: "Alerts", to: "/alerts", icon: Bell, group: "analytics" },
  { label: "Medical review", to: "/review", icon: Stethoscope, group: "operations" },
  { label: "Data sources", to: "/data-sources", icon: Database, group: "operations" },
  { label: "Settings", to: "/settings", icon: Settings, group: "operations" },
];

export default function Layout() {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const { activeAstronautId, setActiveAstronautId } = useCrewSelection();
  const crew = useQuery({ queryKey: ["crew"], queryFn: () => listAstronauts() });
  const alerts = useQuery({ queryKey: ["alert-count"], queryFn: () => getAlerts() });
  const overview = useQuery({ queryKey: ["dashboard"], queryFn: getDashboard });
  const routeAstronautId = new URLSearchParams(location.search).get("astronaut") || location.pathname.match(/^\/crew\/([^/]+)/)?.[1] || "";
  useEffect(() => {
    if (routeAstronautId && crew.data?.some((person) => person.id === routeAstronautId)) setActiveAstronautId(routeAstronautId);
  }, [crew.data, routeAstronautId, setActiveAstronautId]);
  useEffect(() => {
    if (!crew.data?.length) return;
    const currentIsValid = crew.data.some((person) => person.id === activeAstronautId);
    const routeIsValid = !!routeAstronautId && crew.data.some((person) => person.id === routeAstronautId);
    if (!currentIsValid && !routeIsValid) setActiveAstronautId(crew.data[0].id);
  }, [activeAstronautId, crew.data, routeAstronautId, setActiveAstronautId]);
  const activeAstronaut = crew.data?.find((person) => person.id === activeAstronautId) || crew.data?.[0];
  const count = alerts.data?.filter((item) => item.status === "open").length || 0;
  const groups = ["overview", "health", "analytics", "operations"];
  const titles: Record<string, string> = { overview: "Overview", health: "Long-duration health", analytics: "Analytics", operations: "Operations" };
  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    navigate("/crew?q=" + encodeURIComponent(search));
    setOpen(false);
  };
  return <div className="app-frame">
    <button className="mobile-menu" onClick={() => setOpen(!open)} aria-label="Toggle navigation">{open ? <X /> : <Menu />}</button>
    {open && <button className="sidebar-backdrop" aria-label="Close navigation" onClick={() => setOpen(false)} />}
    <aside className={"sidebar " + (open ? "sidebar-open" : "")}>
      <div className="brand"><div className="brand-mark"><Orbit size={18} /></div><div><strong>ASTROGUARD</strong><span>CREW HEALTH SYSTEM</span></div></div>
      <div className="mission-switch"><div className="mission-orbit"><Activity size={15} /></div><div><small>ACTIVE MISSION</small><strong>{overview.data?.mission_name || "Connecting…"}</strong></div><ChevronDown size={14} /></div>
      <nav className="main-nav">
        {groups.map((group) => <div className="nav-group" key={group}>
          <div className="nav-caption">{titles[group]}</div>
          {navItems.filter((item) => item.group === group).map(({ label, to, icon: Icon }) => <NavLink key={to} to={to} end={to === "/"} onClick={() => setOpen(false)} className={({ isActive }) => "nav-link " + (isActive ? "active" : "")}>
            <Icon size={15} strokeWidth={1.8} /><span>{label}</span>{label === "Alerts" && count > 0 && <em>{count}</em>}
          </NavLink>)}
        </div>)}
      </nav>
      <div className="sidebar-bottom"><div className="live-chip"><span /> Systems online</div><div className="user-card"><Avatar name="Dr. Rivera" color="#258694" size="sm" /><div><strong>Dr. Rivera</strong><span>Flight surgeon</span></div><ChevronDown size={13} /></div></div>
    </aside>
    <main className="main-area">
      <header className="topbar">
        <div className="topbar-context"><div className="context-icon"><Shield size={15} /></div><div><span>ASTROGUARD / MISSION CONTROL</span><strong>Spaceflight health intelligence</strong></div></div>
        <form className="global-search" onSubmit={submitSearch}><Search size={15} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search crew or callsign..." /><kbd>↵</kbd></form>
        <label className="global-crew-select" title="Change the active astronaut"><Users size={15} /><span><small>ACTIVE ASTRONAUT</small><select aria-label="Change active astronaut" value={activeAstronaut?.id || ""} onChange={(event) => setActiveAstronautId(event.target.value)}>{crew.data?.map((person) => <option key={person.id} value={person.id}>{person.callsign} · {person.full_name}</option>)}</select></span></label>
        <button className="icon-button notification-button" onClick={() => navigate("/alerts")} aria-label="Open alerts"><Bell size={17} />{count > 0 && <i />}</button>
        <div className="top-profile"><Avatar name="Dr. Rivera" color="#258694" size="sm" /><span>Dr. Rivera</span><ChevronDown size={13} /></div>
      </header>
      <div className="content-area"><Outlet /></div>
    </main>
  </div>;
}
