import { EmptyState } from "../components/EmptyState.js";

export function Comparison() {
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Algorithm Comparison</h1>
        <p className="page-caption">
          Empirical evaluation of Backtracking, Heuristics (MRV/Degree/LCV), Forward
          Checking, and MAC.
        </p>
      </div>

      <EmptyState
        title="No Benchmark Results Loaded"
        description="Run benchmarks or load saved experimental datasets to view performance curves."
      />
    </div>
  );
}
