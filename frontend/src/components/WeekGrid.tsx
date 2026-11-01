import { useMemo } from "react";
import type { Entry, GridDto } from "../api/types";
import { buildWeekGrid } from "../lib/weekGrid";
import { courseColor } from "../lib/colors";
import { formatTimeRange } from "../lib/slots";

interface WeekGridProps {
  entries: Entry[];
  grid: GridDto;
  visibleDays: number[];
  allCourseIds?: string[];
}

export function WeekGrid({
  entries,
  grid,
  visibleDays,
  allCourseIds = [],
}: WeekGridProps) {
  const slotsPerDay = grid.slot_starts.length;
  const timeLabels = useMemo(() => {
    return grid.slot_starts.map((start, i) =>
      formatTimeRange(start, grid.slot_ends[i] || "")
    );
  }, [grid.slot_starts, grid.slot_ends]);

  const gridModel = useMemo(() => {
    return buildWeekGrid(entries, slotsPerDay, visibleDays);
  }, [entries, slotsPerDay, visibleDays]);

  const courseIds = useMemo(() => {
    if (allCourseIds.length > 0) return allCourseIds;
    return Array.from(new Set(entries.map((e) => e.course_id)));
  }, [entries, allCourseIds]);

  // Compute uncovered cells for blocks mode
  const uncoveredCells = useMemo(() => {
    if (gridModel.mode !== "blocks") return [];
    const occupied = new Set<string>();
    for (const b of gridModel.blocks) {
      for (let r = b.rowStart; r < b.rowStart + b.rowSpan; r++) {
        occupied.add(`${b.col},${r}`);
      }
    }
    const empty: { col: number; row: number }[] = [];
    for (let c = 0; c < visibleDays.length; c++) {
      for (let r = 0; r < slotsPerDay; r++) {
        if (!occupied.has(`${c},${r}`)) {
          empty.push({ col: c, row: r });
        }
      }
    }
    return empty;
  }, [gridModel, visibleDays.length, slotsPerDay]);

  const cols = visibleDays.length;
  const rows = slotsPerDay;

  return (
    <div className="weekgrid-wrapper" style={{ overflowX: "auto" }}>
      <div
        className="weekgrid-container"
        style={{
          display: "grid",
          gridTemplateColumns: `90px repeat(${cols}, minmax(130px, 1fr))`,
          gridTemplateRows: `auto repeat(${rows}, minmax(64px, auto))`,
          gap: "1px",
          backgroundColor: "var(--border)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-md)",
          overflow: "hidden",
        }}
      >
        {/* Top-left empty header cell */}
        <div
          style={{
            gridColumn: 1,
            gridRow: 1,
            backgroundColor: "var(--bg-surface-subtle)",
            padding: "10px 8px",
            fontWeight: 600,
            fontSize: "0.8rem",
            color: "var(--text-muted)",
            textAlign: "center",
          }}
        >
          Time
        </div>

        {/* Day Header row */}
        {visibleDays.map((dayIdx, colIdx) => (
          <div
            key={dayIdx}
            style={{
              gridColumn: colIdx + 2,
              gridRow: 1,
              backgroundColor: "var(--bg-surface-subtle)",
              padding: "10px 8px",
              fontWeight: 700,
              fontSize: "0.9rem",
              color: "var(--text-primary)",
              textAlign: "center",
            }}
          >
            {grid.day_names[dayIdx] || `Day ${dayIdx}`}
          </div>
        ))}

        {/* Time label column (1st column) */}
        {timeLabels.map((timeText, rowIdx) => (
          <div
            key={rowIdx}
            style={{
              gridColumn: 1,
              gridRow: rowIdx + 2,
              backgroundColor: "var(--bg-surface-subtle)",
              padding: "8px 6px",
              fontWeight: 600,
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              textAlign: "center",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {timeText}
          </div>
        ))}

        {/* BLOCKS MODE */}
        {gridModel.mode === "blocks" && (
          <>
            {/* Empty grid background slots */}
            {uncoveredCells.map(({ col, row }) => (
              <div
                key={`empty-${col}-${row}`}
                style={{
                  gridColumn: col + 2,
                  gridRow: row + 2,
                  backgroundColor: "var(--bg-surface)",
                }}
              />
            ))}

            {/* Timetable blocks */}
            {gridModel.blocks.map((b) => {
              const e = b.entry;
              const color = courseColor(e.course_id, courseIds);
              const duration = b.rowSpan;
              const titleText = `${e.course_name} (${e.course_id})\nTeacher: ${e.teacher_name} (${e.teacher_id})\nDivision: ${e.division_name} (${e.division_id})\nRoom: ${e.room_name} (${e.room_id})\nTime: ${e.day_name} ${e.start_time}–${e.end_time} (${duration} slot${duration > 1 ? "s" : ""})`;

              return (
                <div
                  key={e.session_id}
                  title={titleText}
                  className="weekgrid-card"
                  style={{
                    gridColumn: b.col + 2,
                    gridRow: `${b.rowStart + 2} / span ${b.rowSpan}`,
                    backgroundColor: color.backgroundColor,
                    borderLeft: `4px solid ${color.borderColor}`,
                    color: color.textColor,
                    padding: "8px 10px",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    borderRadius: "var(--radius-sm)",
                    margin: "2px",
                    boxShadow: "var(--shadow-sm)",
                    overflow: "hidden",
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontWeight: 700,
                        fontSize: "0.85rem",
                        lineHeight: 1.2,
                        wordBreak: "break-word",
                      }}
                    >
                      {e.course_name}
                    </div>
                    <div style={{ fontSize: "0.75rem", opacity: 0.9, marginTop: "2px" }}>
                      {e.teacher_name}
                    </div>
                    <div style={{ fontSize: "0.75rem", opacity: 0.9 }}>
                      {e.division_name} • {e.room_name}
                    </div>
                  </div>
                  <div
                    style={{
                      fontSize: "0.7rem",
                      opacity: 0.8,
                      marginTop: "4px",
                      display: "flex",
                      justifyContent: "space-between",
                    }}
                  >
                    <span>
                      {e.start_time}–{e.end_time}
                    </span>
                    <span>
                      {duration} slot{duration > 1 ? "s" : ""}
                    </span>
                  </div>
                </div>
              );
            })}
          </>
        )}

        {/* STACKED MODE (Overlap / Conflict) */}
        {gridModel.mode === "stacked" && (
          <>
            {/* Background cells */}
            {Array.from({ length: cols * rows }).map((_, i) => {
              const c = i % cols;
              const r = Math.floor(i / cols);
              return (
                <div
                  key={`bg-${c}-${r}`}
                  style={{
                    gridColumn: c + 2,
                    gridRow: r + 2,
                    backgroundColor: "var(--bg-surface)",
                  }}
                />
              );
            })}

            {/* Stacked entries in cells */}
            {gridModel.cells.map((cell) => (
              <div
                key={`stacked-${cell.col}-${cell.row}`}
                style={{
                  gridColumn: cell.col + 2,
                  gridRow: cell.row + 2,
                  display: "flex",
                  flexDirection: "column",
                  gap: "4px",
                  padding: "4px",
                  overflowY: "auto",
                }}
              >
                {cell.items.map(({ entry: e, cont }) => {
                  const color = courseColor(e.course_id, courseIds);
                  return (
                    <div
                      key={`${e.session_id}-${cont ? "cont" : "start"}`}
                      style={{
                        backgroundColor: color.backgroundColor,
                        borderLeft: `4px solid ${color.borderColor}`,
                        color: color.textColor,
                        padding: "4px 6px",
                        fontSize: "0.75rem",
                        borderRadius: "var(--radius-sm)",
                        opacity: cont ? 0.75 : 1,
                      }}
                    >
                      <strong>{e.course_name}</strong> {cont ? "(cont.)" : ""}
                      <div style={{ fontSize: "0.7rem" }}>
                        {e.teacher_name} • {e.room_name}
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

