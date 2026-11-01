import { NavLink } from "react-router-dom";
import { useApp } from "../state/AppContext.js";
import { deriveStatus } from "../lib/status.js";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: "📊" },
  { to: "/data", label: "Data Management", icon: "📁" },
  { to: "/generate", label: "Generate Timetable", icon: "⚡" },
  { to: "/viewer", label: "Timetable Viewer", icon: "🗓" },
  { to: "/validation", label: "Constraint Validation", icon: "🛡" },
  { to: "/comparison", label: "Algorithm Comparison", icon: "📈" },
  { to: "/repair", label: "Timetable Repair", icon: "🔧" },
];

export function Sidebar() {
  const { state } = useApp();
  const status = deriveStatus(state, false);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>Timetable CSP</h2>
        <div className="tag">Fundamentals of AI</div>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `nav-link ${isActive ? "active" : ""}`
            }
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-source">
          <strong>Source:</strong> {state.sourceLabel}
        </div>
        <div>
          <span
            className="sidebar-status-chip"
            style={{
              backgroundColor: `var(--status-${status.tone}-bg)`,
              color: `var(--status-${status.tone}-text)`,
              border: `1px solid var(--status-${status.tone}-border)`,
            }}
          >
            {status.code}
          </span>
        </div>
      </div>
    </aside>
  );
}
