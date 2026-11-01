import { NavLink } from "react-router-dom";
import { useApp } from "../state/AppContext.js";
import { deriveStatus } from "../lib/status.js";
import { useEffect, useState } from "react";

const NAV_ITEMS = [
  { to: "/workspace", label: "Overview", icon: "01" },
  { to: "/data", label: "Set up data", icon: "02" },
  { to: "/generate", label: "Build schedule", icon: "03" },
  { to: "/viewer", label: "Review timetable", icon: "04" },
  { to: "/validation", label: "Check constraints", icon: "05" },
  { to: "/comparison", label: "Compare methods", icon: "06" },
  { to: "/repair", label: "Repair schedule", icon: "07" },
];

export function Sidebar() {
  const { state } = useApp();
  const status = deriveStatus(state, false);
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    typeof localStorage === "undefined" ? "light" : (localStorage.getItem("unisched-theme") as "light" | "dark") || "light"
  );
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("unisched-theme", theme);
  }, [theme]);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-lockup"><span className="brand-mark">U</span><div><h2>UniSched</h2><div className="tag">Academic planning</div></div></div>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/workspace"}
            className={({ isActive }) =>
              `nav-link ${isActive ? "active" : ""}`
            }
          >
            <span className="nav-index">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <NavLink to="/" end className="nav-link landing-return-link">
          <span className="nav-index" aria-hidden="true">↖</span>
          <span>Back to landing page</span>
        </NavLink>
        <button className="theme-toggle" type="button" onClick={() => setTheme(theme === "light" ? "dark" : "light")} aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}>
          <span className="theme-dot" />{theme === "light" ? "Light appearance" : "Dark appearance"}<span className="theme-switch">{theme === "light" ? "☼" : "☾"}</span>
        </button>
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
