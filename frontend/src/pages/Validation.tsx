import { useState, useMemo } from "react";
import { useApp } from "../state/AppContext";
import { EmptyState } from "../components/EmptyState";
import { MetricCards, type MetricItem } from "../components/MetricCards";
import type { RunOutcome, ViolationType, Violation, GridDto } from "../api/types";
import sampleOutcome from "../tests/fixtures/tiny_outcome.json";

export interface CategoryDefinition {
  id: string;
  name: string;
  types: ViolationType[];
  description: string;
}

export const VALIDATION_CATEGORIES: CategoryDefinition[] = [
  {
    id: "teacher_conflicts",
    name: "Teacher conflicts",
    types: ["TEACHER_CONFLICT"],
    description: "A teacher is assigned to multiple sessions simultaneously.",
  },
  {
    id: "division_conflicts",
    name: "Division conflicts",
    types: ["DIVISION_CONFLICT"],
    description: "A student division is scheduled for multiple sessions simultaneously.",
  },
  {
    id: "room_conflicts",
    name: "Room conflicts",
    types: ["ROOM_CONFLICT"],
    description: "Multiple sessions are assigned to the same room at the same time.",
  },
  {
    id: "capacity",
    name: "Capacity",
    types: ["CAPACITY"],
    description: "The room capacity is smaller than the division student count.",
  },
  {
    id: "room_type",
    name: "Room type",
    types: ["ROOM_TYPE"],
    description: "A lab or specialized course is assigned to an incompatible room type.",
  },
  {
    id: "teacher_availability",
    name: "Teacher availability",
    types: ["TEACHER_UNAVAILABLE"],
    description: "A session is scheduled during slots when the teacher is unavailable.",
  },
  {
    id: "room_availability",
    name: "Room availability",
    types: ["ROOM_UNAVAILABLE"],
    description: "A session is scheduled during slots when the room is unavailable.",
  },
  {
    id: "duration_out_of_range",
    name: "Duration / out of range",
    types: ["DURATION", "OUT_OF_RANGE"],
    description: "A multi-slot session does not fit consecutively or extends past the day.",
  },
  {
    id: "missing_sessions",
    name: "Missing sessions",
    types: ["MISSING_SESSION"],
    description: "A required curriculum session was not assigned to any time or room.",
  },
  {
    id: "duplicate_sessions",
    name: "Duplicate sessions",
    types: ["DUPLICATE_SESSION"],
    description: "The same session was assigned more than once.",
  },
  {
    id: "unknown_sessions_rooms",
    name: "Unknown sessions/rooms",
    types: ["UNKNOWN_SESSION", "UNKNOWN_ROOM"],
    description: "Referenced session ID or room ID does not exist in the instance draft.",
  },
  {
    id: "fixed_assignments",
    name: "Fixed assignments",
    types: ["FIXED_ASSIGNMENT"],
    description: "A pre-pinned session was not assigned to its designated time or room.",
  },
];

function formatDaySlot(day: number | null, slot: number | null, grid?: GridDto | null): string {
  if (day === null && slot === null) return "—";
  let dayStr = "";
  if (day !== null) {
    dayStr = grid?.day_names?.[day] ?? `Day ${day + 1}`;
  }
  let slotStr = "";
  if (slot !== null) {
    const startTime = grid?.slot_starts?.[slot];
    const endTime = grid?.slot_ends?.[slot];
    if (startTime && endTime) {
      slotStr = `${startTime}–${endTime} (Slot ${slot + 1})`;
    } else {
      slotStr = `Slot ${slot + 1}`;
    }
  }

  if (dayStr && slotStr) return `${dayStr}, ${slotStr}`;
  return dayStr || slotStr || "—";
}

export function Validation() {
  const { state } = useApp();
  const [previewSample, setPreviewSample] = useState(false);
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<string>("ALL");

  const activeOutcome = (state.outcome?.validation
    ? state.outcome
    : previewSample
    ? (sampleOutcome as unknown as RunOutcome)
    : null) as RunOutcome | null;

  const validation = activeOutcome?.validation;

  const categoryStats = useMemo(() => {
    if (!validation) return [];
    return VALIDATION_CATEGORIES.map((cat) => {
      const count = cat.types.reduce(
        (sum, t) => sum + (validation.counts_by_type?.[t] ?? 0),
        0
      );
      return {
        ...cat,
        count,
      };
    });
  }, [validation]);

  const filteredViolations = useMemo(() => {
    if (!validation?.violations) return [];
    if (selectedCategoryFilter === "ALL") return validation.violations;
    const cat = VALIDATION_CATEGORIES.find((c) => c.id === selectedCategoryFilter);
    if (!cat) return validation.violations;
    return validation.violations.filter((v) => cat.types.includes(v.type));
  }, [validation, selectedCategoryFilter]);

  if (!validation || !activeOutcome) {
    return (
      <div className="validation-page">
        <div className="page-header">
          <h1 className="page-title">Constraint Validation</h1>
          <p className="page-caption">
            Independent verification of all physical, capacity, and resource constraints.
          </p>
        </div>

        <EmptyState
          title="No Validation Report Yet"
          description="Run a schedule from the Generate page or preview sample validation to inspect constraint verification."
          action={{
            label: "Preview Sample Validation",
            onClick: () => setPreviewSample(true),
          }}
        />
      </div>
    );
  }

  const isValid = activeOutcome.is_valid;
  const totalViolations = validation.violations.length;

  const metricItems: MetricItem[] = [
    {
      label: "Sessions Required",
      value: validation.sessions_required,
      subtext: "Expected weekly sessions in curriculum",
    },
    {
      label: "Sessions Assigned",
      value: validation.sessions_assigned,
      subtext:
        validation.sessions_assigned === validation.sessions_required
          ? "100% placed"
          : `${validation.sessions_required - validation.sessions_assigned} unassigned`,
    },
    {
      label: "Total Hard Violations",
      value: totalViolations,
      subtext:
        totalViolations === 0
          ? "Zero hard conflicts"
          : `${totalViolations} constraint breach(es)`,
    },
  ];

  return (
    <div className="validation-page">
      <div className="page-header">
        <div className="validation-header-row">
          <div>
            <h1 className="page-title">Constraint Validation</h1>
            <p className="validation-independent-caption">
              Checked by an independent validator that does not use the search code.
            </p>
          </div>
          <div className="validation-badge-wrap">
            {isValid ? (
              <span
                className="badge badge-valid validation-big-badge"
                data-testid="validation-badge"
              >
                VALID
              </span>
            ) : (
              <span
                className="badge badge-invalid validation-big-badge"
                data-testid="validation-badge"
              >
                NOT VALID
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="validation-meta-banner">
        <span>
          <strong>Run ID:</strong> {activeOutcome.run_id || "N/A"}
        </span>
        <span>
          <strong>Algorithm:</strong> Config {activeOutcome.algorithm || "A"}
        </span>
        <span>
          <strong>Solver Status:</strong> {activeOutcome.status}
        </span>
        {previewSample && !state.outcome && (
          <span className="sample-badge">Sample Fixture Preview</span>
        )}
      </div>

      <div style={{ marginTop: "16px", marginBottom: "28px" }}>
        <MetricCards items={metricItems} />
      </div>

      {/* 12 Categories Table (All categories in exact order, zeros included) */}
      <div className="card" style={{ marginBottom: "28px" }}>
        <div className="card-header">
          <h2 className="card-title">Constraint Categories Overview</h2>
          <span className="card-subtitle">
            All 12 hard constraint categories checked against physical and policy limits.
          </span>
        </div>

        <div className="table-responsive">
          <table className="editable-table" data-testid="categories-table">
            <thead>
              <tr>
                <th style={{ width: "40px" }}>#</th>
                <th style={{ width: "220px" }}>Category</th>
                <th>Description</th>
                <th style={{ width: "120px", textAlign: "center" }}>Count</th>
                <th style={{ width: "140px", textAlign: "center" }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {categoryStats.map((cat, idx) => (
                <tr key={cat.id}>
                  <td style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                    {idx + 1}
                  </td>
                  <td style={{ fontWeight: 600 }}>{cat.name}</td>
                  <td style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>
                    {cat.description}
                  </td>
                  <td
                    style={{
                      textAlign: "center",
                      fontVariantNumeric: "tabular-nums",
                      fontWeight: cat.count > 0 ? 700 : 400,
                      color: cat.count > 0 ? "var(--status-red-text)" : "inherit",
                    }}
                  >
                    {cat.count}
                  </td>
                  <td style={{ textAlign: "center" }}>
                    {cat.count === 0 ? (
                      <span className="badge badge-valid">Passed (0)</span>
                    ) : (
                      <button
                        type="button"
                        className="badge badge-invalid clickable-badge"
                        onClick={() => setSelectedCategoryFilter(cat.id)}
                        title="Click to filter details table"
                      >
                        Violated ({cat.count})
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Violation Detail Table */}
      <div className="card">
        <div
          className="card-header"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            <h2 className="card-title">Violation Details</h2>
            <span className="card-subtitle">
              {totalViolations === 0
                ? "No constraint violations detected."
                : `Showing ${filteredViolations.length} of ${totalViolations} detected violation(s).`}
            </span>
          </div>

          {totalViolations > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <label
                htmlFor="violation-filter-select"
                style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}
              >
                Filter:
              </label>
              <select
                id="violation-filter-select"
                className="table-input"
                style={{ width: "auto", minWidth: "200px" }}
                value={selectedCategoryFilter}
                onChange={(e) => setSelectedCategoryFilter(e.target.value)}
              >
                <option value="ALL">All Categories ({totalViolations})</option>
                {categoryStats
                  .filter((cat) => cat.count > 0)
                  .map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name} ({cat.count})
                    </option>
                  ))}
              </select>
            </div>
          )}
        </div>

        {totalViolations === 0 ? (
          <div
            style={{
              padding: "32px 16px",
              textAlign: "center",
              color: "var(--status-green-text)",
              backgroundColor: "var(--status-green-bg)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--status-green-border)",
              marginTop: "8px",
            }}
          >
            <div style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: "4px" }}>
              ✓ All Hard Constraints Satisfied
            </div>
            <p style={{ margin: 0, fontSize: "0.9rem" }}>
              Every required session is assigned without room, teacher, capacity, or availability conflicts.
            </p>
          </div>
        ) : (
          <div className="table-responsive" style={{ marginTop: "8px" }}>
            <table className="editable-table" data-testid="violations-table">
              <thead>
                <tr>
                  <th style={{ width: "180px" }}>Type</th>
                  <th style={{ width: "160px" }}>Sessions</th>
                  <th style={{ width: "140px" }}>Resource</th>
                  <th style={{ width: "180px" }}>Day / Time</th>
                  <th>Explanation</th>
                </tr>
              </thead>
              <tbody>
                {filteredViolations.map((v: Violation, idx: number) => (
                  <tr key={idx}>
                    <td>
                      <span className="badge badge-invalid">{v.type}</span>
                    </td>
                    <td>
                      {v.session_ids.length > 0 ? (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                          {v.session_ids.map((sid) => (
                            <code key={sid} className="code-pill">
                              {sid}
                            </code>
                          ))}
                        </div>
                      ) : (
                        <span style={{ color: "var(--text-muted)" }}>—</span>
                      )}
                    </td>
                    <td style={{ fontWeight: 500 }}>{v.resource ?? "—"}</td>
                    <td style={{ fontSize: "0.85rem" }}>
                      {formatDaySlot(v.day, v.slot, activeOutcome.timetable?.grid)}
                    </td>
                    <td style={{ fontSize: "0.85rem", color: "var(--text-primary)" }}>
                      {v.explanation}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
