import { useEffect } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Logo } from "./Logo";

export function AppShell() {
  const location = useLocation();
  useEffect(() => {
    const name =
      {
        "/": "Image provenance",
        "/protect": "Protect an image",
        "/verify": "Verify an image",
        "/about": "About",
      }[location.pathname] ?? "Page not found";
    document.title = `${name} · TraceMark`;
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [location.pathname]);
  return (
    <div className="app-frame">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <header className="site-header">
        <div className="header-inner">
          <Logo />
          <nav aria-label="Main navigation">
            <NavLink to="/" end>
              Home
            </NavLink>
            <NavLink to="/protect">Protect</NavLink>
            <NavLink to="/verify">Verify</NavLink>
            <NavLink to="/about">About</NavLink>
          </nav>
        </div>
      </header>
      <main className="container" id="main-content" tabIndex={-1}>
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="footer-inner">
          <span>Traceable images. Measured evidence.</span>
          <Link to="/about#privacy">Privacy & limitations</Link>
        </div>
      </footer>
    </div>
  );
}
