import { useApp } from "../state/AppContext.js";
import { StatusBanner } from "../components/StatusBanner.js";
import { MetricCards, type MetricItem } from "../components/MetricCards.js";

export function Dashboard() {
  const { state } = useApp();
  const summary = state.applied?.summary;
  const outcome = state.outcome;

  // Five stat cards
  const statItems: MetricItem[] = [
    {
      label: "Courses",
      value: summary ? summary.courses : "—",
      subtext: summary ? "Unique subjects" : "Load an instance",
    },
    {
      label: "Teachers",
      value: summary ? summary.teachers : "—",
      subtext: summary ? "Faculty members" : "Load an instance",
    },
    {
      label: "Rooms",
      value: summary ? summary.rooms : "—",
      subtext: summary ? "Available venues" : "Load an instance",
    },
    {
      label: "Divisions",
      value: summary ? summary.divisions : "—",
      subtext: summary ? "Student cohorts" : "Load an instance",
    },
    {
      label: "Required Weekly Sessions",
      value: summary ? summary.sessions : "—",
      subtext: summary ? "CSP variables |X|" : "Load an instance",
    },
  ];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Intelligent University Timetable Scheduler</h1>
        <p className="page-caption">
          Constraint Satisfaction: backtracking, MRV, Degree, LCV, Forward Checking,
          AC-3/MAC — Fundamentals of AI
        </p>
      </div>

      <StatusBanner />

      <MetricCards items={statItems} />

      {/* Latest search result card */}
      {outcome && (
        <div className="panel">
          <div className="panel-title">
            <span>Latest Search Result</span>
            <span
              className={`badge ${
                outcome.is_valid ? "badge-valid" : "badge-invalid"
              }`}
            >
              {outcome.is_valid ? "✔ VALID" : "✖ NOT VALID"}
            </span>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
              gap: "16px",
            }}
          >
            <div>
              <span className="metric-card-label">Algorithm</span>
              <div style={{ fontSize: "1.2rem", fontWeight: 700, marginTop: "4px" }}>
                Config {outcome.algorithm}
              </div>
            </div>
            <div>
              <span className="metric-card-label">Status</span>
              <div style={{ fontSize: "1.2rem", fontWeight: 700, marginTop: "4px" }}>
                {outcome.status}
              </div>
            </div>
            <div>
              <span className="metric-card-label">Runtime</span>
              <div style={{ fontSize: "1.2rem", fontWeight: 700, marginTop: "4px" }}>
                {outcome.metrics?.runtime_s.toFixed(3)} s
              </div>
            </div>
            <div>
              <span className="metric-card-label">Nodes</span>
              <div style={{ fontSize: "1.2rem", fontWeight: 700, marginTop: "4px" }}>
                {outcome.metrics?.nodes.toLocaleString()}
              </div>
            </div>
            <div>
              <span className="metric-card-label">Attempts</span>
              <div style={{ fontSize: "1.2rem", fontWeight: 700, marginTop: "4px" }}>
                {outcome.metrics?.attempts.toLocaleString()}
              </div>
            </div>
            <div>
              <span className="metric-card-label">Backtracks</span>
              <div style={{ fontSize: "1.2rem", fontWeight: 700, marginTop: "4px" }}>
                {outcome.metrics?.backtracks.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* FAI Concepts Section */}
      <details className="fai-details">
        <summary>About this project / FAI concepts</summary>
        <div className="fai-details-content">
          <p>
            <strong>Agent Description:</strong> An intelligent agent that maps
            university curriculum requirements, teacher availability, division
            enrollments, and physical room constraints into a conflict-free semester
            weekly timetable.
          </p>

          <h3>PEAS Task Environment</h3>
          <table className="fai-table">
            <thead>
              <tr>
                <th>Component</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Performance measure</strong></td>
                <td>
                  0 hard-constraint violations, 100% required sessions assigned,
                  minimized soft penalty (isolated gaps, workload balance, preferences).
                </td>
              </tr>
              <tr>
                <td><strong>Environment</strong></td>
                <td>
                  Days and slots schedule grid, classrooms/laboratories with capacity and
                  type, teachers with availability, student divisions with enrollments.
                </td>
              </tr>
              <tr>
                <td><strong>Actuators</strong></td>
                <td>
                  Assignment actions binding each session variable <code>(c, div, idx)</code>{" "}
                  to a domain value <code>(day, start_slot, room)</code>.
                </td>
              </tr>
              <tr>
                <td><strong>Sensors</strong></td>
                <td>
                  Input instance specification parsed from CSV tables or draft JSON,
                  including availability matrices and pre-fixed assignments.
                </td>
              </tr>
            </tbody>
          </table>

          <h3>Environment Characteristics</h3>
          <ul style={{ paddingLeft: "20px", display: "flex", flexDirection: "column", gap: "6px" }}>
            <li>
              <strong>Fully Observable:</strong> The agent has complete knowledge of all
              teachers, courses, rooms, availability, and constraints before scheduling begins.
            </li>
            <li>
              <strong>Deterministic:</strong> Each assignment action deterministically places a
              session into a chosen slot and room with no stochastic noise.
            </li>
            <li>
              <strong>Static:</strong> Problem inputs, constraints, and resources do not change
              while the search algorithm is running.
            </li>
            <li>
              <strong>Discrete:</strong> Time slots, calendar days, student divisions, rooms, and
              sessions are finite discrete entities.
            </li>
            <li>
              <strong>Single-Agent:</strong> The scheduler operates as the sole decision-maker
              formulating the complete timetable.
            </li>
            <li>
              <strong>Sequential / Episodic:</strong> Within a search episode, assignments are
              sequential—each assignment constrains future domains and affects backtracking.
            </li>
          </ul>

          <h3>State-Space Formulation</h3>
          <ul style={{ paddingLeft: "20px", display: "flex", flexDirection: "column", gap: "6px" }}>
            <li>
              <strong>Initial State:</strong> Empty timetable with 0 sessions assigned.
            </li>
            <li>
              <strong>Actions:</strong> Assigning an unassigned session to a legal domain value{" "}
              <code>(day, start_slot, room)</code> that satisfies unary constraints.
            </li>
            <li>
              <strong>Goal Test:</strong> All required weekly sessions assigned with exactly 0
              hard constraint violations.
            </li>
            <li>
              <strong>Path Cost / Search Effort:</strong> Measured by node expansions, assignment
              attempts, backtracks, and constraint consistency checks.
            </li>
          </ul>

          <h3>Constraint Satisfaction Formulation: CSP = (X, D, C)</h3>
          <p style={{ marginTop: "6px" }}>
            <strong>Variables X:</strong> Exactly one variable per required weekly session{" "}
            <code>(course_id, division_id, session_index)</code>.{" "}
            Total count <code>|X| = {summary ? summary.sessions : "—"}</code>.
          </p>
          <p style={{ marginTop: "4px" }}>
            <strong>Domains D:</strong> Finite set of valid{" "}
            <code>(day, start_slot, room)</code> tuples satisfying session duration, room
            type compatibility, and division capacity.
          </p>
          <p style={{ marginTop: "4px" }}>
            <strong>Constraints C:</strong> Hard binary & unary constraints (no teacher
            double-booking, no division double-booking, no room double-booking, teacher
            availability, room availability, fixed pre-assignments).
          </p>

          <p style={{ marginTop: "14px", fontStyle: "italic", fontWeight: 600 }}>
            No machine learning is used — classical symbolic constraint satisfaction and
            systematic heuristic search.
          </p>
        </div>
      </details>
    </div>
  );
}
