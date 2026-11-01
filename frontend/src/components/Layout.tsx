import { useEffect, useState, type ReactNode } from "react";
import { Sidebar } from "./Sidebar.js";
import { ErrorBoundary } from "./ErrorBoundary.js";
import { health } from "../api/client.js";
import { Link, useLocation } from "react-router-dom";
import { useApp } from "../state/AppContext.js";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const { state } = useApp();
  const [backendHealthy, setBackendHealthy] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        await health();
        if (mounted) setBackendHealthy(true);
      } catch {
        if (mounted) setBackendHealthy(false);
      }
    };

    check();
    const interval = window.setInterval(check, 15000);
    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, []);

  return (
    <div className="app-container">
      <Sidebar />
      <div className="main-wrapper">
        {!backendHealthy && (
          <div className="health-banner" role="alert">
            <span>⚠️</span>
            <span>
              Backend not reachable. Ensure FastAPI is running on port 8000
              (<code>uvicorn api.main:app --port 8000</code>).
            </span>
          </div>
        )}
        <main className="main-content">
          <nav className="journey-nav" aria-label="Scheduling workflow">
            <span className="journey-label">YOUR WORKFLOW</span>
            {[
              { path: "/data", label: "Set up data", done: Boolean(state.applied) },
              { path: "/generate", label: "Build schedule", done: Boolean(state.outcome?.timetable) },
              { path: "/viewer", label: "Review & export", done: Boolean(state.outcome?.is_valid) },
            ].map((step, index) => {
              const active = location.pathname === step.path;
              return <Link key={step.path} to={step.path} className={`journey-step ${active ? "active" : ""} ${step.done ? "done" : ""}`} aria-current={active ? "step" : undefined}><span className="journey-step-number">{step.done ? "✓" : `0${index + 1}`}</span>{step.label}</Link>;
            })}
          </nav>
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
