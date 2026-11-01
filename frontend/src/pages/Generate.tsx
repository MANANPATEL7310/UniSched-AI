import { useState, useId } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useApp } from "../state/AppContext";
import { hasErrors } from "../state/reducer";
import { startRun, cancelRun } from "../api/client";
import { useRunPolling } from "../hooks/useRunPolling";
import { StatusBanner } from "../components/StatusBanner";
import { MetricCards, type MetricItem } from "../components/MetricCards";
import { ALGORITHM_OPTIONS, explainRun } from "../lib/explanations";
import type { Algorithm, RunResponse, RunConfigDto } from "../api/types";

export function Generate() {
  const { state, dispatch, canGenerate } = useApp();
  const navigate = useNavigate();
  const timeLimitId = useId();
  const nodeLimitId = useId();

  const [selectedAlgo, setSelectedAlgo] = useState<Algorithm>("A");
  const [timeLimit, setTimeLimit] = useState<number>(60);
  const [nodeLimit, setNodeLimit] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [busyError, setBusyError] = useState<string | null>(null);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);

  const isRunning = Boolean(state.runId && !state.outcome && !state.runError);

  const handleRunFinished = (r: RunResponse) => {
    setIsCancelling(false);
    dispatch({
      type: "RUN_FINISHED",
      outcome: r.outcome,
      error: r.error,
    });
  };

  const { progress } = useRunPolling(state.runId, handleRunFinished);

  const handleGenerate = async () => {
    if (!canGenerate || !state.applied) return;
    setIsSubmitting(true);
    setBusyError(null);

    try {
      const cfg: RunConfigDto = {
        algorithm: selectedAlgo,
        timeout_s: Number(timeLimit) || 60,
        node_limit: nodeLimit === "" ? null : Number(nodeLimit),
      };

      const res = await startRun(state.applied.draft, cfg);
      dispatch({
        type: "RUN_STARTED",
        runId: res.run_id,
        algorithm: selectedAlgo,
      });
    } catch (err: unknown) {
      const errorObj = err as { status?: number; code?: string; message?: string };
      if (
        errorObj.status === 409 ||
        errorObj.code === "BUSY" ||
        String(errorObj.message).includes("BUSY") ||
        String(errorObj.message).includes("progress")
      ) {
        setBusyError("Another run is in progress.");
      } else {
        setBusyError(errorObj.message || "Failed to start solver run.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!state.runId) return;
    setIsCancelling(true);
    try {
      await cancelRun(state.runId);
    } catch (err) {
      console.error("Cancel failed:", err);
    }
  };

  const totalSessions =
    progress?.total ?? state.applied?.summary.sessions ?? 0;
  const assignedSessions = progress?.assigned ?? 0;
  const progressPct =
    totalSessions > 0
      ? Math.min(100, Math.round((assignedSessions / totalSessions) * 100))
      : 0;

  // Outcome metric cards
  const outcome = state.outcome;
  const outcomeMetrics: MetricItem[] = outcome
    ? [
        {
          label: "Runtime",
          value: `${outcome.metrics.runtime_s.toFixed(3)} s`,
          subtext: "Search execution time",
        },
        {
          label: "Search Nodes",
          value: outcome.metrics.nodes,
          subtext: "Explored state nodes",
        },
        {
          label: "Assignment Attempts",
          value: outcome.metrics.attempts,
          subtext: "Value trial assignments",
        },
        {
          label: "Backtracks",
          value: outcome.metrics.backtracks,
          subtext: "Dead ends undone",
        },
        {
          label: "Consistency Checks",
          value: outcome.metrics.checks,
          subtext: "Constraint consistency tests",
        },
        {
          label: "Values Pruned",
          value: ["C", "D"].includes(outcome.algorithm)
            ? outcome.metrics.values_pruned
            : "n/a",
          subtext: ["C", "D"].includes(outcome.algorithm)
            ? "Filtered during propagation"
            : "Requires propagation (C/D)",
        },
        {
          label: "Domain Wipeouts",
          value: outcome.algorithm === "C" ? outcome.metrics.domain_wipeouts : "n/a",
          subtext:
            outcome.algorithm === "C"
              ? "Forward checking dead-ends"
              : "Requires Forward Checking (C)",
        },
        {
          label: "Root AC-3 Pruned",
          value: outcome.algorithm === "D" ? outcome.metrics.root_pruned : "n/a",
          subtext:
            outcome.algorithm === "D"
              ? "Values filtered before search"
              : "Requires AC-3 / MAC (D)",
        },
      ]
    : [];

  return (
    <div className="generate-page">
      <div className="page-header">
        <h1 className="page-title">Generate Timetable</h1>
        <p className="page-caption">
          Execute CSP search algorithms (Configs A, B, C, D) with custom time and node limits.
        </p>
      </div>

      {/* 1. canGenerate Banner */}
      {!canGenerate && (
        <div
          className="card"
          style={{
            marginBottom: "24px",
            backgroundColor: "var(--status-yellow-bg)",
            borderColor: "var(--status-yellow-border)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <strong style={{ color: "var(--status-yellow-text)" }}>Cannot Start Solver: </strong>
              <span style={{ color: "var(--status-yellow-text)", fontSize: "0.9rem" }}>
                {!state.applied
                  ? "No dataset has been applied yet. Load or enter curriculum data in Data Management."
                  : state.dirty
                  ? "You have unapplied draft edits. Validate & Apply your changes before generating."
                  : hasErrors(state.applied.issues)
                  ? "The active dataset contains validation errors. Fix them before running."
                  : "Dataset validation required."}
              </span>
            </div>
            <Link to="/data" className="btn btn-secondary">
              Go to Data Management
            </Link>
          </div>
        </div>
      )}

      {/* Busy or Request Error */}
      {busyError && (
        <div style={{ marginBottom: "20px" }}>
          <div className="status-banner tone-red" role="alert">
            <span style={{ fontSize: "1.1rem" }}>✖</span>
            <span>{busyError}</span>
          </div>
        </div>
      )}

      {/* 5. Progress Panel (While Running) */}
      {isRunning && (
        <div className="progress-panel" data-testid="progress-panel">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 700 }}>
              Search in Progress (Config {state.runAlgorithm})
            </h3>
            <button
              type="button"
              className="btn btn-danger"
              onClick={handleCancel}
              disabled={isCancelling}
            >
              {isCancelling ? "Cancelling…" : "Cancel Search"}
            </button>
          </div>

          <div className="progress-bar-track">
            <div
              className="progress-bar-fill"
              style={{ width: `${progressPct}%` }}
              role="progressbar"
              aria-valuenow={progressPct}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            <span>
              {assignedSessions} / {totalSessions} sessions assigned ({progressPct}%)
            </span>
            <span>Elapsed: {progress?.elapsed_s?.toFixed(1) ?? "0.0"} s</span>
          </div>

          <div className="progress-stats-row">
            <span className="progress-stat-chip">
              <strong>Nodes:</strong> {progress?.nodes?.toLocaleString() ?? 0}
            </span>
            <span className="progress-stat-chip">
              <strong>Attempts:</strong> {progress?.attempts?.toLocaleString() ?? 0}
            </span>
            <span className="progress-stat-chip">
              <strong>Backtracks:</strong> {progress?.backtracks?.toLocaleString() ?? 0}
            </span>
          </div>
        </div>
      )}

      {/* 2. Algorithm Selection Cards */}
      <div className="card" style={{ marginBottom: "24px" }}>
        <div className="card-header">
          <h2 className="card-title">Select Algorithm</h2>
          <span className="card-subtitle">
            Compare systematic CSP search variants with heuristics and constraint propagation.
          </span>
        </div>

        <div className="algo-grid" role="radiogroup" aria-label="Search Algorithm">
          {ALGORITHM_OPTIONS.map((algo) => {
            const isSelected = selectedAlgo === algo.code;
            return (
              <div
                key={algo.code}
                className={`algo-card ${isSelected ? "selected" : ""}`}
                onClick={() => !isRunning && setSelectedAlgo(algo.code)}
                role="radio"
                aria-checked={isSelected}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === " " || e.key === "Enter") {
                    !isRunning && setSelectedAlgo(algo.code);
                  }
                }}
              >
                <div className="algo-card-header">
                  <div className="algo-card-title">
                    <input
                      type="radio"
                      name="algorithm-selection"
                      checked={isSelected}
                      onChange={() => setSelectedAlgo(algo.code)}
                      disabled={isRunning}
                    />
                    <span>{algo.name}</span>
                  </div>
                  <span className="badge badge-valid">{algo.badge}</span>
                </div>
                <p className="algo-card-desc">{algo.description}</p>
              </div>
            );
          })}
        </div>

        {/* 3. Limits & Controls */}
        <div className="limits-row">
          <div className="limit-field">
            <label htmlFor={timeLimitId}>Time Limit (seconds):</label>
            <input
              id={timeLimitId}
              type="number"
              min="1"
              max="3600"
              value={timeLimit}
              disabled={isRunning || !canGenerate}
              onChange={(e) => setTimeLimit(Math.max(1, Math.min(3600, Number(e.target.value) || 1)))}
            />
          </div>

          <div className="limit-field">
            <label htmlFor={nodeLimitId}>Node Limit (optional):</label>
            <input
              id={nodeLimitId}
              type="number"
              min="1"
              placeholder="None (unlimited)"
              value={nodeLimit}
              disabled={isRunning || !canGenerate}
              onChange={(e) => setNodeLimit(e.target.value)}
            />
          </div>

          <div>
            <button
              type="button"
              className="btn btn-primary"
              style={{ minWidth: "180px", height: "42px" }}
              disabled={!canGenerate || isRunning || isSubmitting}
              onClick={handleGenerate}
            >
              {isSubmitting ? "Starting..." : isRunning ? "Running..." : "Generate Timetable"}
            </button>
          </div>
        </div>
      </div>

      {/* 6. Result Panel (When outcome exists and not running) */}
      {outcome && !isRunning && (
        <div className="card" style={{ marginBottom: "28px" }} data-testid="result-panel">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "16px",
              marginBottom: "16px",
            }}
          >
            <div>
              <h2 className="card-title" style={{ margin: 0 }}>
                Run Outcome: Config {outcome.algorithm}
              </h2>
              <span className="card-subtitle">
                Run ID: {outcome.run_id} • Status: {outcome.status}
              </span>
            </div>
            <div>
              {outcome.is_valid ? (
                <span className="badge badge-valid validation-big-badge">VALID</span>
              ) : (
                <span className="badge badge-invalid validation-big-badge">NOT VALID</span>
              )}
            </div>
          </div>

          <div style={{ marginBottom: "16px" }}>
            <StatusBanner running={false} />
          </div>

          <MetricCards items={outcomeMetrics} />

          {outcome.soft && (
            <div
              style={{
                marginTop: "16px",
                padding: "10px 16px",
                backgroundColor: "var(--bg-surface-subtle)",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border)",
                fontSize: "0.85rem",
              }}
            >
              <strong>Soft Constraints Penalty:</strong> {outcome.soft.total} (Student Gaps: {outcome.soft.student_gap}, Teacher Gaps: {outcome.soft.teacher_gap}, Workload: {outcome.soft.workload}, Preference: {outcome.soft.preference})
            </div>
          )}

          {/* 7. Explain This Run */}
          <details className="explain-run-details" open>
            <summary>Explain this run</summary>
            <ul className="explanation-list">
              {explainRun(outcome).map((sentence, idx) => (
                <li key={idx}>{sentence}</li>
              ))}
            </ul>
          </details>

          {/* Action Navigation Buttons */}
          <div style={{ display: "flex", gap: "12px", marginTop: "20px", flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => navigate("/viewer")}
            >
              Open Timetable Viewer
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate("/validation")}
            >
              Open Constraint Validation
            </button>
          </div>
        </div>
      )}

      {/* Error state */}
      {state.runError && !isRunning && (
        <div className="status-banner tone-red" style={{ marginTop: "16px" }}>
          <span style={{ fontSize: "1.1rem" }}>✖</span>
          <span>
            Search execution error: {state.runError.message || "An unexpected error occurred."}
          </span>
        </div>
      )}
    </div>
  );
}
