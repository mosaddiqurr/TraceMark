import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Archive, BarChart3, BookOpen, Boxes, ChevronDown, FileCheck2, FileOutput, Fingerprint,
  Gauge, ImagePlus, ListChecks, LogOut, Menu, Network, SearchCheck, Settings, ShieldCheck, X,
} from "lucide-react";
import { Logo } from "./Logo";
import { useAuth } from "../auth/AuthContext";

const navigation = [
  { to: "/app", end: true, label: "Overview", icon: Gauge },
  { to: "/app/protect", label: "Protect image", icon: ImagePlus },
  { to: "/app/assets", label: "Asset library", icon: Archive },
  { to: "/app/distributions", label: "Distribution copies", icon: Fingerprint },
  { to: "/app/verify", label: "Verify image", icon: ShieldCheck },
  { to: "/app/trace", label: "Trace search", icon: SearchCheck },
  { to: "/app/collections", label: "Collections", icon: Boxes },
  { to: "/app/scans", label: "Source scanner", icon: Network },
  { to: "/app/lab", label: "Robustness lab", icon: BarChart3 },
  { to: "/app/reports", label: "Reports", icon: FileOutput },
  { to: "/app/jobs", label: "Jobs", icon: ListChecks },
];

const pageTitles: Record<string, string> = {
  "/app": "Evidence overview", "/app/protect": "Protect an image", "/app/assets": "Asset library",
  "/app/distributions": "Distribution copies", "/app/verify": "Verify image", "/app/trace": "Trace search",
  "/app/collections": "Collections", "/app/scans": "Source scanner", "/app/lab": "Robustness laboratory",
  "/app/reports": "Evidence reports", "/app/jobs": "Processing jobs", "/app/settings": "Settings",
  "/app/methodology": "Methodology",
};

export function AppShell() {
  const [open, setOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const title = location.pathname.startsWith("/app/assets/") ? "Asset detail" : pageTitles[location.pathname] ?? "TraceMark";
  const signOut = async () => { await logout(); navigate("/"); };
  return (
    <div className="app-frame">
      <a href="#main-content" className="skip-link">Skip to content</a>
      {open && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setOpen(false)} />}
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="sidebar-head"><Logo /><button className="icon-button mobile-only" onClick={() => setOpen(false)} aria-label="Close navigation"><X /></button></div>
        <p className="nav-label">Workspace</p>
        <nav aria-label="Main navigation">
          {navigation.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)}><Icon aria-hidden="true" />{label}</NavLink>)}
        </nav>
        <div className="sidebar-foot">
          <NavLink to="/app/methodology"><BookOpen aria-hidden="true" />Methodology</NavLink>
          <NavLink to="/app/settings"><Settings aria-hidden="true" />Settings</NavLink>
          <div className="trust-note"><FileCheck2 /><p><strong>Evidence, not certainty.</strong><br />TraceMark reports measurements and their limits.</p></div>
        </div>
      </aside>
      <section className="app-main">
        <header className="topbar">
          <div className="topbar-title"><button className="icon-button menu-button" onClick={() => setOpen(true)} aria-label="Open navigation"><Menu /></button><div><small>TraceMark workspace</small><strong>{title}</strong></div></div>
          <div className="account-wrap">
            <button className="account-button" aria-expanded={accountOpen} onClick={() => setAccountOpen((v) => !v)}><span className="avatar">{user?.display_name?.slice(0, 1).toUpperCase() ?? "U"}</span><span className="account-copy"><strong>{user?.display_name}</strong><small>{user?.email}</small></span><ChevronDown /></button>
            {accountOpen && <div className="account-menu"><button onClick={signOut}><LogOut />Sign out</button></div>}
          </div>
        </header>
        <main id="main-content" className="content" tabIndex={-1}><Outlet /></main>
      </section>
    </div>
  );
}
