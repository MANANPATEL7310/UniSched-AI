import { Link } from "react-router-dom";
import { useEffect, useState } from "react";

const steps = [
  { n: "01", title: "Bring your schedule together", sub: "Courses · people · rooms", className: "flow-input" },
  { n: "02", title: "Find a workable fit", sub: "Rules checked as it plans", className: "flow-solve" },
  { n: "03", title: "See the week clearly", sub: "A timetable you can verify", className: "flow-result" },
];

export function Landing() {
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    typeof localStorage === "undefined" ? "light" : (localStorage.getItem("unisched-theme") as "light" | "dark") || "light"
  );
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("unisched-theme", theme);
  }, [theme]);

  return <div className="landing-page">
    <header className="landing-nav"><Link to="/" className="landing-brand"><span className="brand-mark">U</span><span>UniSched</span></Link><span className="landing-nav-note">University timetable planning</span><button className="landing-theme-toggle" type="button" onClick={() => setTheme(theme === "light" ? "dark" : "light")} aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`} title={`Switch to ${theme === "light" ? "dark" : "light"} theme`}><span aria-hidden="true">{theme === "light" ? "☾" : "☼"}</span><span className="landing-theme-label">{theme === "light" ? "Dark mode" : "Light mode"}</span></button><Link to="/workspace" className="landing-nav-link">Open workspace <span>↗</span></Link></header>
    <main>
      <section className="landing-hero">
        <div className="landing-copy"><div className="eyebrow"><span className="live-dot"/> A BETTER WEEK STARTS HERE</div><h1>Make room for<br/><em>better schedules.</em></h1><p>Bring courses, faculty, and rooms into one thoughtful plan. UniSched works through the constraints, so your team can focus on the people behind the timetable.</p><div className="landing-actions"><Link to="/workspace" className="btn btn-primary">Explore the workspace <span>→</span></Link><Link to="/viewer" className="landing-secondary">See a sample week <span>↓</span></Link></div><div className="landing-proof"><span className="proof-check">✓</span> Conflict checked <span className="proof-divider"/> Explainable decisions <span className="proof-divider"/> Built for real campus needs</div></div>
        <div className="landing-visual" aria-label="Illustration of an organized university week"><div className="visual-orbit orbit-one"/><div className="visual-orbit orbit-two"/><div className="visual-sun"/><div className="visual-label">A WEEK, IN GOOD ORDER <span>• SAMPLE PLAN</span></div><div className="mini-calendar"><div className="mini-calendar-head"><span>WEEK AT A GLANCE</span><span className="calendar-range">MON — FRI</span></div><div className="mini-days"><i/><b>MON</b><b>TUE</b><b>WED</b><b>THU</b><b>FRI</b></div>{["09:00","10:00","11:00","12:00"].map((time,i)=><div className="mini-row" key={time}><span>{time}</span><div className={`mini-event event-${i+1}`} style={{gridColumn:i===1?"3 / 5":i===2?"2 / 4":i===3?"4 / 6":"2 / 3"}}><strong>{["Foundations of AI","Discrete mathematics","Python lab","Open study block"][i]}</strong><small>{["Rao · Room 101","Sharma · Room 102","Lee · Lab 101","A little breathing room"][i]}</small></div></div>)}<div className="calendar-foot"><span className="live-dot"/> 5 sessions placed <span className="calendar-valid">✓ VERIFIED</span></div></div><div className="floating-stamp"><span>0</span><small>overlaps</small></div><div className="visual-caption">Clear choices, checked against the rules.</div></div>
      </section>
      <section className="workflow-section"><div className="workflow-intro"><span className="eyebrow">FROM COMPLEXITY TO CLARITY</span><h2>Three steps to a week<br/>that works.</h2><p>UniSched handles the coordination, then gives you a schedule you can inspect and refine.</p></div><div className="workflow-track">{steps.map((step,i)=><div className={`workflow-step ${step.className}`} key={step.n}><span className="workflow-number">{step.n}</span><div className="workflow-symbol">{i===0?<><i/><i/><i/></>:i===1?<><i/><i/><i/><i/><i/></>:<><i/><i/><i/><i/></>}</div><h3>{step.title}</h3><p>{step.sub}</p>{i<2&&<span className="workflow-arrow">→</span>}</div>)}</div></section>
      <section className="landing-bottom"><span>Made for the many moving parts of campus life.</span><Link to="/workspace">Start with the sample data <span>→</span></Link></section>
    </main>
  </div>;
}
