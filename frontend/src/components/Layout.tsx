import { useEffect, useState, type ReactNode } from "react";
import { Sidebar } from "./Sidebar.js";
import { ErrorBoundary } from "./ErrorBoundary.js";
import { health } from "../api/client.js";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
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
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
