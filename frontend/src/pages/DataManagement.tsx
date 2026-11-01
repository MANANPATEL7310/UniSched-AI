import { EmptyState } from "../components/EmptyState.js";

export function DataManagement() {
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Data Management</h1>
        <p className="page-caption">
          Load sample datasets, upload CSV spreadsheets, or customize schedules.
        </p>
      </div>

      <EmptyState
        title="Data Management Editor"
        description="Dataset loading, tabular editors, and validation will be enabled here in Step B8."
      />
    </div>
  );
}
