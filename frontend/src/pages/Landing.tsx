import { Link } from "react-router-dom";
import { useEffect, useState } from "react";

const steps = [
  { n: "01", title: "Bring your schedule together", sub: "Courses · people · rooms", className: "flow-input" },
  { n: "02", title: "Find a workable fit", sub: "Rules checked as it plans", className: "flow-solve" },
  { n: "03", title: "See the week clearly", sub: "A timetable you can verify", className: "flow-result" },
];

export function Landing() {
  const [previewPhase, setPreviewPhase] = useState(0);
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    typeof localStorage === "undefined" ? "light" : (localStorage.getItem("unisched-theme") as "light" | "dark") || "light"
  );
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("unisched-theme", theme);
  }, [theme]);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setPreviewPhase(5);
      return;
    }
    const timer = window.setInterval(() => setPreviewPhase((phase) => (phase + 1) % 6), 1500);
    return () => window.clearInterval(timer);
  }, []);
  const placedCount = ([0, 4, 11, 19, 24, 24] as const)[previewPhase] ?? 24;
  const phaseLabel = ["Checking availability", "Placing first classes", "Balancing rooms & faculty", "Filling the week", "Verifying the timetable", "Schedule ready to share"][previewPhase];

  return <div className="landing-page">
    <header className="landing-nav"><Link to="/" className="landing-brand"><span className="brand-mark">U</span><span>UniSched</span></Link><span className="landing-nav-note">University timetable planning</span><button className="landing-theme-toggle" type="button" onClick={() => setTheme(theme === "light" ? "dark" : "light")} aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`} title={`Switch to ${theme === "light" ? "dark" : "light"} theme`}><span aria-hidden="true">{theme === "light" ? "☾" : "☼"}</span><span className="landing-theme-label">{theme === "light" ? "Dark mode" : "Light mode"}</span></button><Link to="/workspace" className="landing-nav-link">Open workspace <span>↗</span></Link></header>
    <main>
      <section className="landing-hero">
        <div className="landing-copy"><div className="eyebrow"><span className="live-dot"/> UNIVERSITY SCHEDULING, MADE CLEAR</div><h1><span>Make room for</span><br/><em>better schedules.</em></h1><p>Bring classes, faculty, and rooms into one considered plan. UniSched finds a workable fit, checks the constraints, and gives you a week your whole campus can understand.</p><div className="landing-actions"><Link to="/workspace" className="btn btn-primary">Explore the workspace <span>→</span></Link><Link to="/viewer" className="landing-secondary">See a sample week <span>↓</span></Link></div><div className="landing-proof"><span className="proof-check">✓</span> Conflict checked <span className="proof-divider"/> Explainable decisions <span className="proof-divider"/> Built for real campus needs</div></div>
        <div className="landing-visual" aria-label="Animated preview of the UniSched timetable planning workflow"><div className="visual-orbit orbit-one"/><div className="visual-orbit orbit-two"/><div className="visual-sun"/><div className="visual-label">A CLEARER VIEW OF YOUR WEEK <span>• LIVE WORKFLOW</span></div><div className="product-screen"><div className="screen-topbar"><div className="screen-brand"><span className="screen-brand-mark">U</span> UniSched</div><div className="screen-top-meta"><span className={`screen-status-dot phase-${previewPhase}`}/>{phaseLabel}<span className="screen-avatar">SC</span></div></div><div className="screen-body"><aside className="screen-sidebar"><span className="screen-nav-active"><i/> Overview</span><span><i/> My timetable</span><span><i/> Courses</span><span><i/> Faculty & rooms</span><div className="screen-sidebar-foot"><i/> Fall semester<br/>2026 academic year</div></aside><div className={`screen-main phase-${previewPhase}`}><div className="screen-greeting"><div><small>MONDAY, OCTOBER 12</small><h2>{previewPhase < 3 ? "Finding room for every class." : "Your week, in good shape."}</h2><p>{previewPhase < 3 ? "Checking people, rooms, and availability…" : "Here’s a schedule your team can count on."}</p></div><span className={`screen-ready ${previewPhase < 5 ? "is-working" : ""}`}>{previewPhase < 5 ? <><i/> Planning</> : "✓ Ready to share"}</span></div><div className="screen-stats"><div><small>SESSIONS PLACED</small><strong key={placedCount} className="count-pop">{placedCount}<span>/24</span></strong></div><div><small>CONFLICTS</small><strong className="stat-green">0</strong></div><div><small>ROOMS IN USE</small><strong>{previewPhase < 2 ? "—" : "8"}</strong></div></div><div className="screen-progress" role="progressbar" aria-label="Timetable planning preview" aria-valuenow={Math.round(placedCount / 24 * 100)} aria-valuemin={0} aria-valuemax={100}><i style={{width:`${Math.max(6,placedCount / 24 * 100)}%`}}/></div><div className="screen-week-head"><strong>This week</strong><span>MON　 TUE　 WED　 THU　 FRI</span></div><div className="screen-calendar">{[{time:"09:00",title:"Design systems",meta:"Studio 2 · 32 students",day:1},{time:"10:00",title:"Applied computing",meta:"Lecture hall A · 48 students",day:2},{time:"11:00",title:"Data lab",meta:"Lab 04 · 24 students",day:3},{time:"12:00",title:"Research methods",meta:"Room 206 · 28 students",day:4},{time:"13:00",title:"Project studio",meta:"Studio 1 · 18 students",day:2}].map((item,index)=><div className={`screen-class-row ${previewPhase >= index + 1 ? "is-placed" : ""}`} key={item.time}><small>{item.time}</small><div className="screen-class-block" style={{gridColumn:`${item.day} / span 2`}}><b>{item.title}</b><span>{item.meta}</span></div></div>)}</div><div className="screen-bottom"><span><i/> {previewPhase === 5 ? "Schedule checked against room, faculty, and class availability" : "Checking room, faculty, and class availability"}</span><span>VIEW WEEK　↗</span></div></div></div></div><div className="visual-caption"><span className="preview-live-dot"/> A working preview of the scheduling process</div></div>
      </section>
      <section className="workflow-section"><div className="workflow-intro"><span className="eyebrow">FROM COMPLEXITY TO CLARITY</span><span className="workflow-count">A SIMPLE, THREE-STEP FLOW</span><h2>From moving parts<br/><em>to a week that works.</em></h2><p>UniSched brings the details together, checks every placement, and leaves you with a schedule your team can review and refine.</p></div><div className="workflow-track">{steps.map((step,i)=><article className={`workflow-step ${step.className}`} key={step.n}><div className="workflow-step-top"><span className="workflow-number">STEP {step.n}</span><span className="workflow-card-arrow" aria-hidden="true">↗</span></div><div className="workflow-symbol" aria-hidden="true">{i===0?<><i/><i/><i/></>:i===1?<><i/><i/><i/><i/><i/></>:<><i/><i/><i/><i/></>}</div><h3>{step.title}</h3><p>{step.sub}</p><div className="workflow-step-caption">{["Start with the information you already have.","Let the scheduler work through the constraints.","Review the result and share it with confidence."][i]}</div>{i<2&&<span className="workflow-arrow" aria-hidden="true">→</span>}</article>)}</div></section>
      <section className="landing-bottom"><div className="bottom-cta-mark" aria-hidden="true"><span>U</span></div><div className="bottom-cta-copy"><strong>Ready to see your week differently?</strong><span>Start with a working sample, then make it your own.</span></div><Link to="/workspace" className="bottom-cta-button">Open UniSched <span>→</span></Link></section>
    </main>
  </div>;
}
