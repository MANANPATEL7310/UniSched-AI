import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  cancelBenchmark,
  getSavedResult,
  listSavedResults,
  startBenchmark,
} from "../api/client.js";
import type {
  Algorithm,
  BenchmarkRequest,
  BenchmarkResponse,
  SavedResultInfo,
} from "../api/types.js";
import { EmptyState } from "../components/EmptyState.js";
import { MetricCards, type MetricItem } from "../components/MetricCards.js";
import { useBenchmarkPolling } from "../hooks/useBenchmarkPolling.js";
import { aggregateRows, seriesFor, type SeriesPoint } from "../lib/aggregate.js";
import { useApp } from "../state/AppContext.js";

const ALGO_COLORS: Record<string, string> = {
  A: "#a88a83",
  B: "#e85d24",
  C: "#718c72",
  D: "#d99a32",
};

export function Comparison() {
  const { state, dispatch } = useApp();

  // Benchmark form state
  const [selectedSizes, setSelectedSizes] = useState<
    ("small" | "medium" | "large")[]
  >(["small"]);
  const [selectedAlgos, setSelectedAlgos] = useState<Algorithm[]>([
    "A",
    "B",
    "C",
    "D",
  ]);
  const [seeds, setSeeds] = useState<number>(1);
  const [timeoutS, setTimeoutS] = useState<number>(30);
  const [measureMemory, setMeasureMemory] = useState<boolean>(false);

  // Active benchmark running state
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  // Saved results state
  const [savedFiles, setSavedFiles] = useState<SavedResultInfo[]>([]);
  const [selectedSavedFile, setSelectedSavedFile] = useState<string>("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadingFile, setLoadingFile] = useState<boolean>(false);

  // Chart options
  const [logScale, setLogScale] = useState<boolean>(false);

  // Fetch saved results list on mount
  useEffect(() => {
    let unmounted = false;
    listSavedResults()
      .then((files) => {
        if (!unmounted) {
          setSavedFiles(files);
          if (files.length > 0 && files[0]) {
            setSelectedSavedFile(files[0].name);
          }
        }
      })
      .catch(() => {
        // Silently ignore if results directory is empty
      });
    return () => {
      unmounted = true;
    };
  }, []);

  // Benchmark polling hook
  const { progress } = useBenchmarkPolling(
    activeJobId,
    (res: BenchmarkResponse) => {
      setActiveJobId(null);
      if (res.state === "error") {
        setRunError(res.error?.message || "Benchmark failed");
      } else if (res.rows) {
        dispatch({ type: "SET_BENCH", rows: res.rows, meta: res.meta });
        // Refresh saved files list
        listSavedResults().then(setSavedFiles).catch(() => {});
      }
    }
  );

  const handleStartBenchmark = async () => {
    if (selectedSizes.length === 0 || selectedAlgos.length === 0) {
      setRunError("Please select at least one problem size and one algorithm.");
      return;
    }
    setRunError(null);
    try {
      const req: BenchmarkRequest = {
        sizes: selectedSizes,
        algorithms: selectedAlgos,
        seeds,
        timeout_s: timeoutS,
        measure_memory: measureMemory,
      };
      const res = await startBenchmark(req);
      setActiveJobId(res.job_id);
    } catch (err: any) {
      setRunError(err.message || "Failed to start benchmark");
    }
  };

  const handleCancelBenchmark = async () => {
    if (!activeJobId) return;
    try {
      await cancelBenchmark(activeJobId);
    } catch (err: any) {
      setRunError(err.message || "Failed to cancel benchmark");
    }
  };

  const handleLoadSaved = async () => {
    if (!selectedSavedFile) return;
    setLoadingFile(true);
    setLoadError(null);
    try {
      const rows = await getSavedResult(selectedSavedFile);
      dispatch({
        type: "SET_BENCH",
        rows,
        meta: { source_file: selectedSavedFile },
      });
    } catch (err: any) {
      setLoadError(err.message || "Failed to load saved benchmark results");
    } finally {
      setLoadingFile(false);
    }
  };

  const toggleSize = (size: "small" | "medium" | "large") => {
    setSelectedSizes((prev) =>
      prev.includes(size) ? prev.filter((s) => s !== size) : [...prev, size]
    );
  };

  const toggleAlgo = (algo: Algorithm) => {
    setSelectedAlgos((prev) =>
      prev.includes(algo) ? prev.filter((a) => a !== algo) : [...prev, algo]
    );
  };

  const rows = state.benchRows || [];
  const aggregated = aggregateRows(rows);

  // Solved vs Unsolved breakdown
  const solvedCount = rows.filter((r) => r.solved && r.valid).length;
  const unsolvedCount = rows.length - solvedCount;

  // Series data for charts
  const runtimeData = seriesFor("runtime_s", rows);
  const nodesData = seriesFor("nodes", rows);
  const backtracksData = seriesFor("backtracks", rows);
  const successData = seriesFor("successRate", rows);
  const softData = seriesFor("soft_penalty", rows);

  // Filter non-positive points if log scale is enabled
  const filterLogData = (data: SeriesPoint[]) => {
    if (!logScale) return data;
    return data.map((pt) => {
      const copy: SeriesPoint = { ...pt };
      for (const k of ["A", "B", "C", "D"] as const) {
        if (copy[k] !== undefined && (copy[k] as number) <= 0) {
          delete copy[k];
        }
      }
      return copy;
    });
  };

  const metricSummaryCards: MetricItem[] = rows.length
    ? [
        {
          label: "Total Runs",
          value: rows.length,
          subtext: `${aggregated.length} configuration groups`,
        },
        {
          label: "Solved & Valid",
          value: solvedCount,
          subtext: `${((solvedCount / rows.length) * 100).toFixed(1)}% success rate`,
        },
        {
          label: "Unsolved / Timed Out",
          value: unsolvedCount,
          subtext: unsolvedCount > 0 ? "Excluded from search effort means" : "0 timeouts",
        },
      ]
    : [];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Algorithm Comparison</h1>
        <p className="page-caption">
          Empirical evaluation of Backtracking (A), Heuristics (B), Forward Checking (C), and MAC (D).
        </p>
      </div>

      {/* Control Panels: Run Benchmark & Load Results */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "16px",
          marginBottom: "24px",
        }}
      >
        {/* Panel 1: Run Benchmark Suite */}
        <div className="panel">
          <h2 className="panel-title" style={{ marginBottom: "12px" }}>
            Run Benchmark Suite
          </h2>

          <div style={{ marginBottom: "12px" }}>
            <label
              style={{
                fontSize: "0.85rem",
                fontWeight: 600,
                color: "var(--text-secondary)",
                display: "block",
                marginBottom: "6px",
              }}
            >
              Instance Sizes:
            </label>
            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
              {(["small", "medium", "large"] as const).map((sz) => (
                <label
                  key={sz}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    fontSize: "0.85rem",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedSizes.includes(sz)}
                    onChange={() => toggleSize(sz)}
                    disabled={activeJobId !== null}
                  />
                  <span style={{ textTransform: "capitalize" }}>{sz}</span>
                </label>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: "12px" }}>
            <label
              style={{
                fontSize: "0.85rem",
                fontWeight: 600,
                color: "var(--text-secondary)",
                display: "block",
                marginBottom: "6px",
              }}
            >
              Algorithms:
            </label>
            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
              {(["A", "B", "C", "D"] as const).map((algo) => (
                <label
                  key={algo}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    fontSize: "0.85rem",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedAlgos.includes(algo)}
                    onChange={() => toggleAlgo(algo)}
                    disabled={activeJobId !== null}
                  />
                  <span>
                    <strong>{algo}</strong> (
                    {algo === "A"
                      ? "BT"
                      : algo === "B"
                        ? "MRV/LCV"
                        : algo === "C"
                          ? "FC"
                          : "MAC"}
                    )
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px",
              marginBottom: "12px",
            }}
          >
            <div>
              <label
                style={{
                  fontSize: "0.85rem",
                  fontWeight: 600,
                  color: "var(--text-secondary)",
                  display: "block",
                  marginBottom: "4px",
                }}
              >
                Seeds (1–5):
              </label>
              <input
                type="number"
                min={1}
                max={5}
                value={seeds}
                onChange={(e) => setSeeds(Math.max(1, Math.min(5, parseInt(e.target.value) || 1)))}
                disabled={activeJobId !== null}
                className="table-input"
              />
            </div>
            <div>
              <label
                style={{
                  fontSize: "0.85rem",
                  fontWeight: 600,
                  color: "var(--text-secondary)",
                  display: "block",
                  marginBottom: "4px",
                }}
              >
                Timeout (s):
              </label>
              <input
                type="number"
                min={1}
                max={600}
                value={timeoutS}
                onChange={(e) => setTimeoutS(Math.max(1, parseInt(e.target.value) || 30))}
                disabled={activeJobId !== null}
                className="table-input"
              />
            </div>
          </div>

          <div style={{ marginBottom: "16px" }}>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "0.85rem",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={measureMemory}
                onChange={(e) => setMeasureMemory(e.target.checked)}
                disabled={activeJobId !== null}
              />
              <span>Measure peak memory with tracemalloc (slower)</span>
            </label>
          </div>

          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--text-muted)",
              marginBottom: "14px",
              lineHeight: 1.4,
              backgroundColor: "var(--bg-surface-subtle)",
              padding: "8px 10px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            <em>
              Note: Large instances with algorithm A may hit the time limit; this is reported, not hidden.
            </em>
          </div>

          {activeJobId ? (
            <div>
              <div style={{ marginBottom: "8px", fontSize: "0.85rem", fontWeight: 600 }}>
                Benchmark running...{" "}
                {progress ? `${progress.done} / ${progress.total} completed` : "Initializing..."}
              </div>
              <div
                style={{
                  width: "100%",
                  height: "8px",
                  backgroundColor: "var(--border)",
                  borderRadius: "4px",
                  overflow: "hidden",
                  marginBottom: "12px",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: progress && progress.total > 0 ? `${(progress.done / progress.total) * 100}%` : "0%",
                    backgroundColor: "var(--primary)",
                    transition: "width 0.3s ease",
                  }}
                />
              </div>
              <button onClick={handleCancelBenchmark} className="btn btn-secondary" style={{ width: "100%" }}>
                Cancel Benchmark
              </button>
            </div>
          ) : (
            <button onClick={handleStartBenchmark} className="btn btn-primary" style={{ width: "100%" }}>
              Run Benchmark
            </button>
          )}

          {runError && (
            <div
              style={{
                marginTop: "12px",
                color: "var(--status-red-text)",
                backgroundColor: "var(--status-red-bg)",
                padding: "8px",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.85rem",
              }}
            >
              {runError}
            </div>
          )}
        </div>

        {/* Panel 2: Load Saved Benchmark Results */}
        <div className="panel">
          <h2 className="panel-title" style={{ marginBottom: "12px" }}>
            Load Saved Results
          </h2>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "16px" }}>
            Inspect previously recorded experiment datasets stored on disk in the results folder.
          </p>

          <div style={{ marginBottom: "16px" }}>
            <label
              style={{
                fontSize: "0.85rem",
                fontWeight: 600,
                color: "var(--text-secondary)",
                display: "block",
                marginBottom: "6px",
              }}
            >
              Saved Results File:
            </label>
            <select
              value={selectedSavedFile}
              onChange={(e) => setSelectedSavedFile(e.target.value)}
              className="table-input"
              disabled={savedFiles.length === 0 || loadingFile}
            >
              {savedFiles.length === 0 ? (
                <option value="">No saved results found on server</option>
              ) : (
                savedFiles.map((f) => (
                  <option key={f.name} value={f.name}>
                    {f.name} ({f.rows} rows - {new Date(f.created).toLocaleString()})
                  </option>
                ))
              )}
            </select>
          </div>

          <button
            onClick={handleLoadSaved}
            disabled={!selectedSavedFile || loadingFile}
            className="btn btn-secondary"
            style={{ width: "100%" }}
          >
            {loadingFile ? "Loading..." : "Load Dataset"}
          </button>

          {loadError && (
            <div
              style={{
                marginTop: "12px",
                color: "var(--status-red-text)",
                backgroundColor: "var(--status-red-bg)",
                padding: "8px",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.85rem",
              }}
            >
              {loadError}
            </div>
          )}
        </div>
      </div>

      {/* Main Results Display */}
      {rows.length === 0 ? (
        <EmptyState
          title="No Benchmark Results Loaded"
          description="Run benchmarks or load saved experimental datasets to view performance curves and empirical scaling comparisons."
        />
      ) : (
        <div>
          {/* High-level summary metrics */}
          <div style={{ marginBottom: "20px" }}>
            <MetricCards items={metricSummaryCards} />
          </div>

          {/* Section: Summary Aggregation Table */}
          <div className="panel" style={{ marginBottom: "24px" }}>
            <h2 className="panel-title" style={{ marginBottom: "12px" }}>
              Summary by Algorithm & Problem Size (Solved Runs)
            </h2>
            <div style={{ overflowX: "auto" }}>
              <table className="editable-table" style={{ width: "100%" }}>
                <thead>
                  <tr>
                    <th scope="col">Size</th>
                    <th scope="col">Algorithm</th>
                    <th scope="col">Total (N)</th>
                    <th scope="col">Solved</th>
                    <th scope="col">Success Rate</th>
                    <th scope="col">Mean Runtime (s)</th>
                    <th scope="col">Mean Nodes</th>
                    <th scope="col">Mean Backtracks</th>
                    <th scope="col">Mean Soft Score</th>
                  </tr>
                </thead>
                <tbody>
                  {aggregated.map((agg, idx) => (
                    <tr key={idx}>
                      <td style={{ textTransform: "capitalize", fontWeight: 600 }}>{agg.size_label}</td>
                      <td>
                        <span
                          style={{
                            fontWeight: 700,
                            color: ALGO_COLORS[agg.algorithm] || "inherit",
                          }}
                        >
                          Algorithm {agg.algorithm}
                        </span>
                      </td>
                      <td>{agg.n}</td>
                      <td>{agg.solved}</td>
                      <td>{(agg.successRate * 100).toFixed(1)}%</td>
                      <td>{agg.mean_runtime_s !== undefined ? `${agg.mean_runtime_s.toFixed(3)} s` : "—"}</td>
                      <td>{agg.mean_nodes !== undefined ? agg.mean_nodes.toLocaleString() : "—"}</td>
                      <td>{agg.mean_backtracks !== undefined ? agg.mean_backtracks.toLocaleString() : "—"}</td>
                      <td>{agg.mean_soft_penalty !== undefined ? agg.mean_soft_penalty.toFixed(2) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Section: Comparative Charts */}
          <div className="panel" style={{ marginBottom: "24px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                marginBottom: "16px",
              }}
            >
              <h2 className="panel-title">Performance & Scaling Curves</h2>
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  fontSize: "0.85rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={logScale}
                  onChange={(e) => setLogScale(e.target.checked)}
                />
                <span>Logarithmic Scale for Search Effort</span>
              </label>
            </div>

            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "20px" }}>
              Charts 1–3 use only solved runs; {unsolvedCount} unsolved run(s) excluded.
            </p>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(450px, 1fr))",
                gap: "24px",
              }}
            >
              {/* Chart 1: Runtime */}
              <div style={{ backgroundColor: "var(--bg-surface-subtle)", padding: "16px", borderRadius: "var(--radius-md)" }}>
                <h3 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "12px", textAlign: "center" }}>
                  1. Search Runtime (seconds) vs. Number of Sessions
                </h3>
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={filterLogData(runtimeData)} margin={{ top: 10, right: 25, left: 10, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.4} />
                    <XAxis dataKey="num_sessions" label={{ value: "Number of Sessions", position: "insideBottom", offset: -10 }} />
                    <YAxis scale={logScale ? "log" : "auto"} domain={logScale ? ["auto", "auto"] : [0, "auto"]} />
                    <Tooltip />
                    <Legend verticalAlign="top" height={36} />
                    <Line type="monotone" dataKey="A" stroke={ALGO_COLORS.A} strokeWidth={2} name="Algo A (BT)" />
                    <Line type="monotone" dataKey="B" stroke={ALGO_COLORS.B} strokeWidth={2} name="Algo B (Heuristics)" />
                    <Line type="monotone" dataKey="C" stroke={ALGO_COLORS.C} strokeWidth={2} name="Algo C (FC)" />
                    <Line type="monotone" dataKey="D" stroke={ALGO_COLORS.D} strokeWidth={2} name="Algo D (MAC)" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Chart 2: Nodes Visited */}
              <div style={{ backgroundColor: "var(--bg-surface-subtle)", padding: "16px", borderRadius: "var(--radius-md)" }}>
                <h3 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "12px", textAlign: "center" }}>
                  2. Search Tree Nodes Visited vs. Sessions
                </h3>
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={filterLogData(nodesData)} margin={{ top: 10, right: 25, left: 10, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.4} />
                    <XAxis dataKey="num_sessions" label={{ value: "Number of Sessions", position: "insideBottom", offset: -10 }} />
                    <YAxis scale={logScale ? "log" : "auto"} domain={logScale ? ["auto", "auto"] : [0, "auto"]} />
                    <Tooltip />
                    <Legend verticalAlign="top" height={36} />
                    <Line type="monotone" dataKey="A" stroke={ALGO_COLORS.A} strokeWidth={2} name="Algo A (BT)" />
                    <Line type="monotone" dataKey="B" stroke={ALGO_COLORS.B} strokeWidth={2} name="Algo B (Heuristics)" />
                    <Line type="monotone" dataKey="C" stroke={ALGO_COLORS.C} strokeWidth={2} name="Algo C (FC)" />
                    <Line type="monotone" dataKey="D" stroke={ALGO_COLORS.D} strokeWidth={2} name="Algo D (MAC)" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Chart 3: Backtracks */}
              <div style={{ backgroundColor: "var(--bg-surface-subtle)", padding: "16px", borderRadius: "var(--radius-md)" }}>
                <h3 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "12px", textAlign: "center" }}>
                  3. Search Backtracks vs. Sessions
                </h3>
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={filterLogData(backtracksData)} margin={{ top: 10, right: 25, left: 10, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.4} />
                    <XAxis dataKey="num_sessions" label={{ value: "Number of Sessions", position: "insideBottom", offset: -10 }} />
                    <YAxis scale={logScale ? "log" : "auto"} domain={logScale ? ["auto", "auto"] : [0, "auto"]} />
                    <Tooltip />
                    <Legend verticalAlign="top" height={36} />
                    <Line type="monotone" dataKey="A" stroke={ALGO_COLORS.A} strokeWidth={2} name="Algo A (BT)" />
                    <Line type="monotone" dataKey="B" stroke={ALGO_COLORS.B} strokeWidth={2} name="Algo B (Heuristics)" />
                    <Line type="monotone" dataKey="C" stroke={ALGO_COLORS.C} strokeWidth={2} name="Algo C (FC)" />
                    <Line type="monotone" dataKey="D" stroke={ALGO_COLORS.D} strokeWidth={2} name="Algo D (MAC)" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Chart 4: Success Rate */}
              <div style={{ backgroundColor: "var(--bg-surface-subtle)", padding: "16px", borderRadius: "var(--radius-md)" }}>
                <h3 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "12px", textAlign: "center" }}>
                  4. Success Rate (%) by Algorithm
                </h3>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={successData} margin={{ top: 10, right: 25, left: 10, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.4} />
                    <XAxis dataKey="num_sessions" label={{ value: "Number of Sessions", position: "insideBottom", offset: -10 }} />
                    <YAxis domain={[0, 100]} />
                    <Tooltip />
                    <Legend verticalAlign="top" height={36} />
                    <Bar dataKey="A" fill={ALGO_COLORS.A} name="Algo A" />
                    <Bar dataKey="B" fill={ALGO_COLORS.B} name="Algo B" />
                    <Bar dataKey="C" fill={ALGO_COLORS.C} name="Algo C" />
                    <Bar dataKey="D" fill={ALGO_COLORS.D} name="Algo D" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Chart 5: Soft Constraint Penalty */}
              <div style={{ backgroundColor: "var(--bg-surface-subtle)", padding: "16px", borderRadius: "var(--radius-md)" }}>
                <h3 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "12px", textAlign: "center" }}>
                  5. Soft Constraint Penalty (Solved Runs Only)
                </h3>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={softData} margin={{ top: 10, right: 25, left: 10, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.4} />
                    <XAxis dataKey="num_sessions" label={{ value: "Number of Sessions", position: "insideBottom", offset: -10 }} />
                    <YAxis />
                    <Tooltip />
                    <Legend verticalAlign="top" height={36} />
                    <Bar dataKey="A" fill={ALGO_COLORS.A} name="Algo A" />
                    <Bar dataKey="B" fill={ALGO_COLORS.B} name="Algo B" />
                    <Bar dataKey="C" fill={ALGO_COLORS.C} name="Algo C" />
                    <Bar dataKey="D" fill={ALGO_COLORS.D} name="Algo D" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Section: Raw Detail Table */}
          <div className="panel" style={{ marginBottom: "24px" }}>
            <h2 className="panel-title" style={{ marginBottom: "12px" }}>
              Raw Benchmark Execution Log
            </h2>
            <div style={{ overflowX: "auto" }}>
              <table className="editable-table" style={{ width: "100%", fontSize: "0.8rem" }}>
                <thead>
                  <tr>
                    <th scope="col">Algo</th>
                    <th scope="col">Instance</th>
                    <th scope="col">Size</th>
                    <th scope="col"># Sessions</th>
                    <th scope="col">Seed</th>
                    <th scope="col">Status</th>
                    <th scope="col">Solved</th>
                    <th scope="col">Valid</th>
                    <th scope="col">Runtime (s)</th>
                    <th scope="col">Nodes</th>
                    <th scope="col">Backtracks</th>
                    <th scope="col">Pruned</th>
                    <th scope="col">Peak Mem (KB)</th>
                    <th scope="col">Violations</th>
                    <th scope="col">Soft Penalty</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i}>
                      <td>
                        <strong>{r.algorithm}</strong>
                      </td>
                      <td>{r.instance}</td>
                      <td style={{ textTransform: "capitalize" }}>{r.size_label}</td>
                      <td>{r.num_sessions}</td>
                      <td>{r.seed}</td>
                      <td>
                        <span
                          className={`badge ${
                            r.status === "SOLVED"
                              ? "badge-valid"
                              : r.status === "TIMEOUT"
                                ? "badge-warning"
                                : "badge-invalid"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td>{r.solved ? "Yes" : "No"}</td>
                      <td>{r.valid ? "Yes" : "No"}</td>
                      <td>{r.runtime_s.toFixed(3)}</td>
                      <td>{r.nodes.toLocaleString()}</td>
                      <td>{r.backtracks.toLocaleString()}</td>
                      <td>{r.values_pruned.toLocaleString()}</td>
                      <td>{r.peak_memory_kb !== null ? r.peak_memory_kb.toFixed(1) : "—"}</td>
                      <td>{r.hard_violations}</td>
                      <td>{r.soft_penalty !== null ? r.soft_penalty.toFixed(1) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Fixed Caption per specification */}
          <div
            style={{
              padding: "12px 16px",
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-md)",
              fontSize: "0.85rem",
              color: "var(--text-secondary)",
              lineHeight: 1.5,
              fontStyle: "italic",
            }}
          >
            "Heuristics can reduce search effort, but the benefit depends on problem structure. These numbers are measured on the listed instances; they are not guarantees."
          </div>
        </div>
      )}
    </div>
  );
}
