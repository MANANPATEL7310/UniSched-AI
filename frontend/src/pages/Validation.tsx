import { EmptyState } from "../components/EmptyState.js";

export function Validation() {
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Constraint Validation</h1>
        <p className="page-caption">
          Independent verification of all physical, capacity, and resource constraints.
        </p>
      </div>

      <EmptyState
        title="No Validation Report Yet"
        description="Run a schedule to view the independent validator's verification report."
      />
    </div>
  );
}
