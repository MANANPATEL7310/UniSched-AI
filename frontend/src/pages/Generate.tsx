import { EmptyState } from "../components/EmptyState.js";

export function Generate() {
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Generate Timetable</h1>
        <p className="page-caption">
          Execute CSP search algorithms (Configs A, B, C, D) with custom time limits.
        </p>
      </div>

      <EmptyState
        title="Solver Engine"
        description="Search execution and real-time polling will be connected here."
      />
    </div>
  );
}
