import { useMemo, useState } from "react";
import { useApp } from "../state/AppContext";
import { EmptyState } from "../components/EmptyState";
import { WeekGrid } from "../components/WeekGrid";
import { timetableCsvUrl } from "../api/client";
import { downloadCsvBlob, entriesToCsv } from "../lib/csv";
import type { Entry, RunOutcome } from "../api/types";
import tinyOutcomeFixture from "../tests/fixtures/tiny_outcome.json";

type ViewBy = "All" | "Division" | "Teacher" | "Room" | "Course";
type DisplayMode = "calendar" | "table";

export function Viewer() {
  const { state, dispatch } = useApp();
  const outcome = state.outcome;
  const timetable = outcome?.timetable;
  const entries = timetable?.entries || [];
  const grid = timetable?.grid;

  const [viewBy, setViewBy] = useState<ViewBy>("All");
  const [selectedEntity, setSelectedEntity] = useState<string>("");
  const [displayMode, setDisplayMode] = useState<DisplayMode>("calendar");

  // Selected days: defaults to all days from grid
  const allDays = useMemo(() => {
    if (!grid) return [];
    return grid.day_names.map((_, i) => i);
  }, [grid]);

  const [selectedDays, setSelectedDays] = useState<number[]>([]);

  // Initialize selected days when grid loads
  const activeDays = selectedDays.length > 0 ? selectedDays : allDays;

  // Options for entity select
  const entityOptions = useMemo(() => {
    if (viewBy === "All") return [];
    const map = new Map<string, string>();
    for (const e of entries) {
      if (viewBy === "Division") map.set(e.division_id, e.division_name);
      else if (viewBy === "Teacher") map.set(e.teacher_id, e.teacher_name);
      else if (viewBy === "Room") map.set(e.room_id, e.room_name);
      else if (viewBy === "Course") map.set(e.course_id, e.course_name);
    }
    return Array.from(map.entries())
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [entries, viewBy]);

  // Set default entity on viewBy change
  const currentEntity = selectedEntity || entityOptions[0]?.id || "";

  // Client-side filtering of entries
  const filteredEntries = useMemo(() => {
    return entries.filter((e) => {
      // Filter by days
      if (!activeDays.includes(e.day)) return false;

      // Filter by entity
      if (viewBy === "Division") return e.division_id === currentEntity;
      if (viewBy === "Teacher") return e.teacher_id === currentEntity;
      if (viewBy === "Room") return e.room_id === currentEntity;
      if (viewBy === "Course") return e.course_id === currentEntity;
      return true;
    });
  }, [entries, activeDays, viewBy, currentEntity]);

  // Sort state for table mode
  const [sortCol, setSortCol] = useState<keyof Entry>("day");
  const [sortAsc, setSortAsc] = useState<boolean>(true);

  const sortedTableEntries = useMemo(() => {
    return [...filteredEntries].sort((a, b) => {
      const va = a[sortCol];
      const vb = b[sortCol];
      if (typeof va === "number" && typeof vb === "number") {
        return sortAsc ? va - vb : vb - va;
      }
      return sortAsc
        ? String(va).localeCompare(String(vb))
        : String(vb).localeCompare(String(va));
    });
  }, [filteredEntries, sortCol, sortAsc]);

  const handleToggleDay = (dayIdx: number) => {
    if (activeDays.includes(dayIdx)) {
      if (activeDays.length > 1) {
        setSelectedDays(activeDays.filter((d) => d !== dayIdx));
      }
    } else {
      setSelectedDays([...activeDays, dayIdx]);
    }
  };

  const handleLoadFixture = () => {
    dispatch({
      type: "RUN_FINISHED",
      outcome: tinyOutcomeFixture as unknown as RunOutcome,
      error: null,
    });
  };

  // 1. Empty State if no outcome or timetable
  if (!outcome || !timetable || !grid) {
    const description = outcome
      ? `The last run did not produce a timetable (${outcome.status}): ${outcome.message}`
      : "No timetable has been generated yet. Run a search from the Generate page, or preview the sample solution fixture.";

    return (
      <div>
        <div className="page-header">
          <h1 className="page-title">Timetable Viewer</h1>
          <p className="page-caption">
            Weekly calendar and tabular representation of scheduled sessions.
          </p>
        </div>

        <EmptyState
          title="No Timetable Available"
          description={description}
          action={{
            label: "Preview Sample Solution (Tiny Fixture)",
            onClick: handleLoadFixture,
          }}
        />
      </div>
    );
  }

  const allCourseIds = Array.from(new Set(entries.map((e) => e.course_id)));

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <h1 className="page-title">Timetable Viewer</h1>
          {!outcome.is_valid && (
            <span className="badge badge-invalid" style={{ fontSize: "0.85rem" }}>
              ✖ NOT VALID
            </span>
          )}
          {outcome.is_valid && (
            <span className="badge badge-valid" style={{ fontSize: "0.85rem" }}>
              ✔ VALID
            </span>
          )}
        </div>
        <p className="page-caption">
          Viewing timetable for <strong>{state.applied?.draft?.name || "Current Instance"}</strong> (
          {outcome.algorithm} — {outcome.status})
        </p>
      </div>

      {/* 2. Red banner if not valid */}
      {!outcome.is_valid && (
        <div className="status-banner tone-red" role="alert" style={{ marginBottom: "20px" }}>
          <span>✖</span>
          <span>
            The solver returned a timetable but the independent validator found violations. Do not use
            it.
          </span>
        </div>
      )}

      {/* 3. Controls Bar */}
      <div
        className="panel"
        style={{
          padding: "16px 20px",
          display: "flex",
          flexWrap: "wrap",
          gap: "16px",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", flexWrap: "wrap", gap: "16px", alignItems: "center" }}>
          {/* View by */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <label htmlFor="view-by-select" style={{ fontWeight: 600, fontSize: "0.85rem" }}>
              View By:
            </label>
            <select
              id="view-by-select"
              className="table-input"
              style={{ width: "130px" }}
              value={viewBy}
              onChange={(e) => {
                setViewBy(e.target.value as ViewBy);
                setSelectedEntity("");
              }}
            >
              <option value="All">All</option>
              <option value="Division">Division</option>
              <option value="Teacher">Teacher</option>
              <option value="Room">Room</option>
              <option value="Course">Course</option>
            </select>
          </div>

          {/* Entity select (hidden for All) */}
          {viewBy !== "All" && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <label htmlFor="entity-select" style={{ fontWeight: 600, fontSize: "0.85rem" }}>
                Select {viewBy}:
              </label>
              <select
                id="entity-select"
                className="table-input"
                style={{ width: "180px" }}
                value={currentEntity}
                onChange={(e) => setSelectedEntity(e.target.value)}
              >
                {entityOptions.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.name} ({opt.id})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Days checkboxes */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>Days:</span>
            <div style={{ display: "flex", gap: "6px" }}>
              {grid.day_names.map((dayName, idx) => {
                const isChecked = activeDays.includes(idx);
                return (
                  <label
                    key={dayName}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                      fontSize: "0.8rem",
                      cursor: "pointer",
                      padding: "2px 6px",
                      borderRadius: "var(--radius-sm)",
                      border: `1px solid ${isChecked ? "var(--border-focus)" : "var(--border)"}`,
                      backgroundColor: isChecked ? "var(--status-blue-bg)" : "var(--bg-surface)",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => handleToggleDay(idx)}
                    />
                    <span>{dayName}</span>
                  </label>
                );
              })}
            </div>
          </div>
        </div>

        {/* Display mode + Exports */}
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <div style={{ display: "flex", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", overflow: "hidden" }}>
            <button
              type="button"
              className={`btn ${displayMode === "calendar" ? "btn-primary" : "btn-secondary"}`}
              style={{ padding: "5px 12px", fontSize: "0.8rem", borderRadius: 0 }}
              onClick={() => setDisplayMode("calendar")}
            >
              Calendar
            </button>
            <button
              type="button"
              className={`btn ${displayMode === "table" ? "btn-primary" : "btn-secondary"}`}
              style={{ padding: "5px 12px", fontSize: "0.8rem", borderRadius: 0 }}
              onClick={() => setDisplayMode("table")}
            >
              Table
            </button>
          </div>

          {state.runId && (
            <a
              className="btn btn-secondary"
              style={{ padding: "5px 12px", fontSize: "0.8rem" }}
              href={timetableCsvUrl(state.runId)}
              download={`timetable_${state.runId}.csv`}
            >
              Full CSV
            </a>
          )}

          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: "5px 12px", fontSize: "0.8rem" }}
            onClick={() =>
              downloadCsvBlob(entriesToCsv(filteredEntries), "timetable_filtered.csv")
            }
          >
            Filtered CSV
          </button>
        </div>
      </div>

      {/* Main Grid or Table view */}
      <div className="panel" style={{ padding: "20px" }}>
        {filteredEntries.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
            No scheduled sessions match the selected filters.
          </div>
        ) : displayMode === "calendar" ? (
          <WeekGrid
            entries={filteredEntries}
            grid={grid}
            visibleDays={activeDays}
            allCourseIds={allCourseIds}
          />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="editable-table">
              <thead>
                <tr>
                  <th
                    scope="col"
                    style={{ cursor: "pointer" }}
                    onClick={() => {
                      if (sortCol === "day") setSortAsc(!sortAsc);
                      else {
                        setSortCol("day");
                        setSortAsc(true);
                      }
                    }}
                  >
                    Day {sortCol === "day" ? (sortAsc ? "▲" : "▼") : ""}
                  </th>
                  <th
                    scope="col"
                    style={{ cursor: "pointer" }}
                    onClick={() => {
                      if (sortCol === "start_time") setSortAsc(!sortAsc);
                      else {
                        setSortCol("start_time");
                        setSortAsc(true);
                      }
                    }}
                  >
                    Start {sortCol === "start_time" ? (sortAsc ? "▲" : "▼") : ""}
                  </th>
                  <th scope="col">End</th>
                  <th scope="col">Duration (slots)</th>
                  <th
                    scope="col"
                    style={{ cursor: "pointer" }}
                    onClick={() => {
                      if (sortCol === "course_name") setSortAsc(!sortAsc);
                      else {
                        setSortCol("course_name");
                        setSortAsc(true);
                      }
                    }}
                  >
                    Course {sortCol === "course_name" ? (sortAsc ? "▲" : "▼") : ""}
                  </th>
                  <th
                    scope="col"
                    style={{ cursor: "pointer" }}
                    onClick={() => {
                      if (sortCol === "teacher_name") setSortAsc(!sortAsc);
                      else {
                        setSortCol("teacher_name");
                        setSortAsc(true);
                      }
                    }}
                  >
                    Teacher {sortCol === "teacher_name" ? (sortAsc ? "▲" : "▼") : ""}
                  </th>
                  <th scope="col">Division</th>
                  <th
                    scope="col"
                    style={{ cursor: "pointer" }}
                    onClick={() => {
                      if (sortCol === "room_name") setSortAsc(!sortAsc);
                      else {
                        setSortCol("room_name");
                        setSortAsc(true);
                      }
                    }}
                  >
                    Room {sortCol === "room_name" ? (sortAsc ? "▲" : "▼") : ""}
                  </th>
                  <th scope="col">Session ID</th>
                </tr>
              </thead>
              <tbody>
                {sortedTableEntries.map((e) => (
                  <tr key={e.session_id}>
                    <td><strong>{e.day_name}</strong></td>
                    <td>{e.start_time}</td>
                    <td>{e.end_time}</td>
                    <td>{e.duration_slots}</td>
                    <td><strong>{e.course_name}</strong> ({e.course_id})</td>
                    <td>{e.teacher_name}</td>
                    <td>{e.division_name}</td>
                    <td>{e.room_name}</td>
                    <td><code>{e.session_id}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ marginTop: "16px", fontSize: "0.8rem", color: "var(--text-muted)", textAlign: "center" }}>
          This weekly timetable repeats every week of the semester.
        </div>
      </div>
    </div>
  );
}
