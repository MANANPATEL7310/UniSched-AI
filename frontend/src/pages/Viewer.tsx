import { EmptyState } from "../components/EmptyState.js";

export function Viewer() {
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Timetable Viewer</h1>
        <p className="page-caption">
          Interactive weekly calendar and tabular timetable display.
        </p>
      </div>

      <EmptyState
        title="No Timetable Generated Yet"
        description="Run a scheduling algorithm or load a solution to inspect the weekly timetable."
      />
    </div>
  );
}
