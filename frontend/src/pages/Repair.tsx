import { useState } from "react";
import { Link } from "react-router-dom";
import { useApp } from "../state/AppContext.js";
import { improveSoftConstraints, repair } from "../api/client.js";
import type {
  LockPolicy,
  RepairChangeType,
  RepairResponse,
  SoftImproveResponse,
} from "../api/types.js";

export function Repair() {
  const { state, dispatch } = useApp();

  const [changeType, setChangeType] = useState<RepairChangeType>("teacher_unavailable");
  const [selectedEntityId, setSelectedEntityId] = useState<string>("");
  const [selectedDay, setSelectedDay] = useState<number>(0);
  const [selectedSlot, setSelectedSlot] = useState<number>(0);
  const [lockPolicy, setLockPolicy] = useState<LockPolicy>("relax_neighbors");

  const [loading, setLoading] = useState<boolean>(false);
  const [optimizing, setOptimizing] = useState<boolean>(false);
  const [repairResult, setRepairResult] = useState<RepairResponse | null>(null);
  const [softResult, setSoftResult] = useState<SoftImproveResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [publishedSuccess, setPublishedSuccess] = useState<boolean>(false);

  const draft = state.draft;
  const outcome = state.outcome;
  const timetable = outcome?.timetable;

  // Determine selectable entities
  const teachers = draft?.teachers || [];
  const rooms = draft?.rooms || [];
  const days = draft?.days || ["Mon", "Tue", "Wed", "Thu", "Fri"];
  const slots = draft?.slots || [];

  // Default entity selection if not set
  const currentEntityId =
    selectedEntityId ||
    (changeType === "teacher_unavailable"
      ? teachers[0]?.teacher_id || ""
      : rooms[0]?.room_id || "");

  // Build published TimetableDraft JSON format
  const getPublishedJson = () => {
    if (!timetable || !draft) return null;
    const assignments: Record<string, [number, number, string]> = {};
    for (const entry of timetable.entries) {
      assignments[entry.session_id] = [entry.day, entry.start_slot, entry.room_id];
    }
    return {
      instance_name: draft.name,
      assignments,
    };
  };

  const handleRepair = async () => {
    if (!draft || !timetable) return;
    const publishedJson = getPublishedJson();
    if (!publishedJson) return;

    setLoading(true);
    setErrorMsg(null);
    setPublishedSuccess(false);

    try {
      const res = await repair({
        draft,
        published: publishedJson,
        change: {
          type: changeType,
          entity_id: currentEntityId,
          day: selectedDay,
          slot: selectedSlot,
        },
        lock_policy: lockPolicy,
        timeout_s: 15,
      });
      setRepairResult(res);
      setSoftResult(null);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to repair timetable.");
    } finally {
      setLoading(false);
    }
  };

  const handleImproveSoft = async () => {
    if (!draft || !timetable) return;
    const publishedJson = getPublishedJson();
    if (!publishedJson) return;

    setOptimizing(true);
    setErrorMsg(null);
    setPublishedSuccess(false);

    try {
      const res = await improveSoftConstraints({
        draft,
        published: publishedJson,
        max_steps: 100,
        time_limit_s: 3,
      });
      setSoftResult(res);
      if (res.outcome) {
        setRepairResult({
          status: res.status,
          outcome: res.outcome,
          diff: [],
          relaxed_locks: [],
          change_penalty: 0,
          message: res.message,
        });
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to optimize soft constraints.");
    } finally {
      setOptimizing(false);
    }
  };

  const handlePublish = () => {
    if (!repairResult?.outcome) return;
    dispatch({
      type: "RUN_FINISHED",
      outcome: repairResult.outcome,
      error: null,
    });
    setPublishedSuccess(true);
  };

  if (!draft || !outcome || !timetable) {
    return (
      <div className="page-container">
        <h1>Timetable Repair & Rescheduling</h1>
        <div className="card" style={{ padding: "2rem", textAlign: "center" }}>
          <p style={{ fontSize: "1.1rem", marginBottom: "1rem" }}>
            No published timetable found in current session.
          </p>
          <p style={{ color: "var(--text-muted)", marginBottom: "1.5rem" }}>
            Generate a timetable solution first on the Generate page or load a sample preset.
          </p>
          <Link to="/generate" className="button button-primary">
            Go to Generate Page
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <header className="page-header">
        <h1>Timetable Repair & Rescheduling</h1>
        <p className="page-subtitle">
          Inject real-world resource disruptions and execute minimal-change constraint repair
          with relaxation rings and independent interval validation.
        </p>
      </header>

      {errorMsg && (
        <div className="error-banner" role="alert" style={{ marginBottom: "1rem" }}>
          <span>⚠️ {errorMsg}</span>
        </div>
      )}

      {publishedSuccess && (
        <div className="success-banner" role="status" style={{ marginBottom: "1rem" }}>
          <span>✅ Revised timetable published successfully! Updated across Viewer and Validation.</span>
        </div>
      )}

      {softResult && (
        <div className="info-banner" role="status" style={{ marginBottom: "1rem" }}>
          <span>🌱 {softResult.message} ({softResult.steps_accepted} improvement step(s) accepted).</span>
        </div>
      )}

      <div className="grid-2-col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        {/* Panel 1: Inject Disruption */}
        <div className="card">
          <h2>1. Inject Unavailability Disruption</h2>
          <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
              <input
                type="radio"
                name="disruptionType"
                checked={changeType === "teacher_unavailable"}
                onChange={() => {
                  setChangeType("teacher_unavailable");
                  setSelectedEntityId(teachers[0]?.teacher_id || "");
                }}
              />
              Teacher Unavailable
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
              <input
                type="radio"
                name="disruptionType"
                checked={changeType === "room_unavailable"}
                onChange={() => {
                  setChangeType("room_unavailable");
                  setSelectedEntityId(rooms[0]?.room_id || "");
                }}
              />
              Room Unavailable
            </label>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem" }}>
                {changeType === "teacher_unavailable" ? "Affected Teacher" : "Affected Room"}
              </label>
              <select
                className="input-select"
                value={currentEntityId}
                onChange={(e) => setSelectedEntityId(e.target.value)}
                style={{ width: "100%", padding: "0.5rem" }}
              >
                {changeType === "teacher_unavailable"
                  ? teachers.map((t) => (
                      <option key={t.teacher_id} value={t.teacher_id}>
                        {t.teacher_name ? `${t.teacher_name} (${t.teacher_id})` : t.teacher_id}
                      </option>
                    ))
                  : rooms.map((r) => (
                      <option key={r.room_id} value={r.room_id}>
                        {r.room_name ? `${r.room_name} (${r.room_id})` : r.room_id} [{r.room_type}]
                      </option>
                    ))}
              </select>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem" }}>
                  Day
                </label>
                <select
                  className="input-select"
                  value={selectedDay}
                  onChange={(e) => setSelectedDay(Number(e.target.value))}
                  style={{ width: "100%", padding: "0.5rem" }}
                >
                  {days.map((d, idx) => (
                    <option key={d} value={idx}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem" }}>
                  Time Slot
                </label>
                <select
                  className="input-select"
                  value={selectedSlot}
                  onChange={(e) => setSelectedSlot(Number(e.target.value))}
                  style={{ width: "100%", padding: "0.5rem" }}
                >
                  {slots.map((s, idx) => (
                    <option key={idx} value={idx}>
                      Slot {idx} ({s.start} - {s.end})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Panel 2: Policy & Execution */}
        <div className="card">
          <h2>2. Locking Policy & Repair Actions</h2>
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem" }}>
              Session Pinning Strategy
            </label>
            <select
              className="input-select"
              value={lockPolicy}
              onChange={(e) => setLockPolicy(e.target.value as LockPolicy)}
              style={{ width: "100%", padding: "0.5rem" }}
            >
              <option value="relax_neighbors">
                Relax Neighbors (Progressive Rings: only unlock sharing sessions)
              </option>
              <option value="strict">
                Strict Freezing (Lock ALL unaffected sessions to old slots)
              </option>
              <option value="free">
                Free Re-solve (Keep distance preference without hard locks)
              </option>
            </select>
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
              Minimal disruption: free sessions search assignments nearest their original slot first.
            </p>
          </div>

          <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.5rem" }}>
            <button
              type="button"
              className="button button-primary"
              disabled={loading || optimizing}
              onClick={handleRepair}
              style={{ flex: 1 }}
            >
              {loading ? "Repairing..." : "⚡ Repair Timetable"}
            </button>
            <button
              type="button"
              className="button button-secondary"
              disabled={loading || optimizing}
              onClick={handleImproveSoft}
              title="Run hill-climbing local search to reduce gaps and teacher idle time"
            >
              {optimizing ? "Optimizing..." : "🌱 Optimize Soft Constraints"}
            </button>
          </div>
        </div>
      </div>

      {/* Repair Outcome & Diff Section */}
      {repairResult && (
        <div className="card" style={{ marginTop: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <div>
              <h2>Repair Outcome: {repairResult.status}</h2>
              <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>{repairResult.message}</p>
            </div>
            {repairResult.outcome && (
              <button
                type="button"
                className="button button-primary"
                onClick={handlePublish}
                style={{ backgroundColor: "var(--status-green-border, #10b981)" }}
              >
                ✓ Publish Revised Timetable
              </button>
            )}
          </div>

          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
            <div className="metric-badge">
              <strong>Assignments Changed:</strong> {repairResult.change_penalty}
            </div>
            <div className="metric-badge">
              <strong>Locks Relaxed:</strong> {repairResult.relaxed_locks.length}
            </div>
            {repairResult.outcome?.validation && (
              <div
                className="metric-badge"
                style={{
                  color: repairResult.outcome.validation.is_valid ? "#065f46" : "#991b1b",
                  backgroundColor: repairResult.outcome.validation.is_valid ? "#d1fae5" : "#fee2e2",
                }}
              >
                <strong>Independent Validator:</strong>{" "}
                {repairResult.outcome.validation.is_valid ? "PASSED (0 Conflicts)" : "INVALID"}
              </div>
            )}
            {repairResult.outcome?.soft && (
              <div className="metric-badge">
                <strong>Soft Penalty:</strong> {repairResult.outcome.soft.total}
              </div>
            )}
          </div>

          {repairResult.relaxed_locks.length > 0 && (
            <div style={{ padding: "0.75rem", backgroundColor: "var(--bg-subtle, #f3f4f6)", borderRadius: "4px", marginBottom: "1rem", fontSize: "0.85rem" }}>
              <strong>Relaxed Session Locks:</strong> {repairResult.relaxed_locks.join(", ")}
            </div>
          )}

          {repairResult.diff.length > 0 && (
            <div>
              <h3>Assignment Changes & Diff</h3>
              <div style={{ overflowX: "auto" }}>
                <table className="data-table" style={{ width: "100%", fontSize: "0.85rem" }}>
                  <thead>
                    <tr>
                      <th>Session ID</th>
                      <th>Course</th>
                      <th>Division</th>
                      <th>Teacher</th>
                      <th>Original Slot & Room</th>
                      <th>New Slot & Room</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {repairResult.diff.map((d) => (
                      <tr
                        key={d.session_id}
                        style={{
                          backgroundColor: d.change_type !== "UNCHANGED" ? "var(--row-highlight, #fef3c7)" : undefined,
                        }}
                      >
                        <td><code>{d.session_id}</code></td>
                        <td>{d.course_name}</td>
                        <td>{d.division_name}</td>
                        <td>{d.teacher_name}</td>
                        <td>
                          {d.old_day !== null
                            ? `${days[d.old_day] || `Day ${d.old_day}`} Slot ${d.old_slot} (${d.old_room_id})`
                            : "None"}
                        </td>
                        <td>
                          <strong>
                            {`${days[d.new_day] || `Day ${d.new_day}`} Slot ${d.new_slot} (${d.new_room_id})`}
                          </strong>
                        </td>
                        <td>
                          <span
                            className="tag"
                            style={{
                              backgroundColor:
                                d.change_type === "UNCHANGED"
                                  ? "#e5e7eb"
                                  : d.change_type === "MOVED_BOTH"
                                  ? "#fde68a"
                                  : "#bfdbfe",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              fontSize: "0.75rem",
                            }}
                          >
                            {d.change_type}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Repair;
