import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Comparison } from "../pages/Comparison.js";
import { AppContext, type AppContextValue } from "../state/AppContext.js";
import type { AppState } from "../state/reducer.js";
import type { BenchmarkRow } from "../api/types.js";

const sampleBenchmarkRows: BenchmarkRow[] = [
  {
    instance: "small_s0",
    size_label: "small",
    num_sessions: 45,
    seed: 0,
    algorithm: "A",
    status: "SOLVED",
    solved: true,
    valid: true,
    runtime_s: 0.123,
    build_s: 0.015,
    nodes: 150,
    attempts: 180,
    backtracks: 12,
    checks: 210,
    values_pruned: 0,
    peak_memory_kb: null,
    hard_violations: 0,
    soft_penalty: 3.5,
    timeout_s: 30.0,
  },
  {
    instance: "small_s0",
    size_label: "small",
    num_sessions: 45,
    seed: 0,
    algorithm: "B",
    status: "SOLVED",
    solved: true,
    valid: true,
    runtime_s: 0.045,
    build_s: 0.012,
    nodes: 50,
    attempts: 55,
    backtracks: 1,
    checks: 70,
    values_pruned: 0,
    peak_memory_kb: null,
    hard_violations: 0,
    soft_penalty: 2.0,
    timeout_s: 30.0,
  },
];

function makeContextValue(stateOverrides?: Partial<AppState>): AppContextValue {
  const baseState: AppState = {
    draft: null,
    applied: null,
    dirty: false,
    sourceLabel: "sample",
    runId: null,
    runAlgorithm: null,
    outcome: null,
    runError: null,
    benchRows: null,
    benchMeta: null,
  };

  return {
    state: { ...baseState, ...stateOverrides },
    dispatch: () => {},
    canGenerate: false,
  };
}

describe("Comparison page", () => {
  it("renders empty state and controls when no results loaded", () => {
    const ctx = makeContextValue({ benchRows: null });

    render(
      <AppContext.Provider value={ctx}>
        <Comparison />
      </AppContext.Provider>
    );

    expect(screen.getByRole("heading", { name: "Algorithm Comparison" })).toBeInTheDocument();
    expect(screen.getByText("No Benchmark Results Loaded")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Benchmark" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load Dataset" })).toBeInTheDocument();
    expect(
      screen.getByText(/Large instances with algorithm A may hit the time limit/i)
    ).toBeInTheDocument();
  });

  it("renders summary table, charts, raw table, and fixed caption when benchRows loaded", () => {
    const ctx = makeContextValue({ benchRows: sampleBenchmarkRows });

    render(
      <AppContext.Provider value={ctx}>
        <Comparison />
      </AppContext.Provider>
    );

    // Header & Metric cards
    expect(screen.getByRole("heading", { name: "Algorithm Comparison" })).toBeInTheDocument();
    expect(screen.getByText("Total Runs")).toBeInTheDocument();
    expect(screen.getByText("Solved & Valid")).toBeInTheDocument();

    // Summary table content
    expect(screen.getByText("Summary by Algorithm & Problem Size (Solved Runs)")).toBeInTheDocument();
    expect(screen.getByText("Algorithm A")).toBeInTheDocument();
    expect(screen.getByText("Algorithm B")).toBeInTheDocument();

    // Raw execution log table
    expect(screen.getByText("Raw Benchmark Execution Log")).toBeInTheDocument();
    expect(screen.getAllByText("small_s0")).toHaveLength(2);

    // Performance curves heading
    expect(screen.getByText("Performance & Scaling Curves")).toBeInTheDocument();
    expect(screen.getByText(/Charts 1–3 use only solved runs/i)).toBeInTheDocument();

    // Log scale toggle
    const logToggle = screen.getByLabelText(/Logarithmic Scale for Search Effort/i);
    expect(logToggle).not.toBeChecked();
    fireEvent.click(logToggle);
    expect(logToggle).toBeChecked();

    // Required fixed caption verbatim
    expect(
      screen.getByText(
        /"Heuristics can reduce search effort, but the benefit depends on problem structure\. These numbers are measured on the listed instances; they are not guarantees\."/i
      )
    ).toBeInTheDocument();
  });
});
