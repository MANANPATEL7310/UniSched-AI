import { describe, expect, it } from "vitest";
import { aggregateRows, seriesFor } from "../lib/aggregate.js";
import type { BenchmarkRow } from "../api/types.js";

const makeRow = (overrides: Partial<BenchmarkRow>): BenchmarkRow => ({
  instance: "inst1",
  size_label: "small",
  num_sessions: 30,
  seed: 0,
  algorithm: "A",
  status: "SOLVED",
  solved: true,
  valid: true,
  runtime_s: 0.1,
  build_s: 0.02,
  nodes: 100,
  attempts: 120,
  backtracks: 10,
  checks: 150,
  values_pruned: 0,
  peak_memory_kb: null,
  hard_violations: 0,
  soft_penalty: 5.0,
  timeout_s: 10.0,
  ...overrides,
});

describe("aggregateRows", () => {
  it("returns empty array for empty inputs", () => {
    expect(aggregateRows([])).toEqual([]);
  });

  it("aggregates solved and unsolved rows correctly", () => {
    const rows: BenchmarkRow[] = [
      makeRow({ algorithm: "A", size_label: "small", runtime_s: 0.1, nodes: 100, backtracks: 10, soft_penalty: 4.0 }),
      makeRow({ algorithm: "A", size_label: "small", runtime_s: 0.3, nodes: 200, backtracks: 20, soft_penalty: 6.0 }),
      makeRow({
        algorithm: "A",
        size_label: "small",
        status: "TIMEOUT",
        solved: false,
        valid: false,
        runtime_s: 10.0,
        nodes: 5000,
        backtracks: 2000,
        soft_penalty: null,
      }),
      makeRow({ algorithm: "B", size_label: "small", runtime_s: 0.05, nodes: 40, backtracks: 0, soft_penalty: 2.0 }),
    ];

    const agg = aggregateRows(rows);
    expect(agg).toHaveLength(2);

    const aggA = agg.find((a) => a.algorithm === "A" && a.size_label === "small");
    expect(aggA).toBeDefined();
    expect(aggA?.n).toBe(3);
    expect(aggA?.solved).toBe(2);
    expect(aggA?.successRate).toBeCloseTo(2 / 3);
    // Solved runs only for means: (0.1 + 0.3)/2 = 0.2
    expect(aggA?.mean_runtime_s).toBeCloseTo(0.2);
    // (100 + 200)/2 = 150
    expect(aggA?.mean_nodes).toBe(150);
    // (10 + 20)/2 = 15
    expect(aggA?.mean_backtracks).toBe(15);
    // (4.0 + 6.0)/2 = 5.0
    expect(aggA?.mean_soft_penalty).toBeCloseTo(5.0);

    const aggB = agg.find((a) => a.algorithm === "B" && a.size_label === "small");
    expect(aggB).toBeDefined();
    expect(aggB?.n).toBe(1);
    expect(aggB?.solved).toBe(1);
    expect(aggB?.successRate).toBe(1.0);
    expect(aggB?.mean_runtime_s).toBeCloseTo(0.05);
    expect(aggB?.mean_nodes).toBe(40);
  });

  it("handles algorithm with 0 solved runs", () => {
    const rows: BenchmarkRow[] = [
      makeRow({
        algorithm: "A",
        size_label: "large",
        status: "TIMEOUT",
        solved: false,
        valid: false,
        runtime_s: 30.0,
      }),
    ];

    const agg = aggregateRows(rows);
    expect(agg).toHaveLength(1);
    const item = agg[0]!;
    expect(item.n).toBe(1);
    expect(item.solved).toBe(0);
    expect(item.successRate).toBe(0.0);
    expect(item.mean_runtime_s).toBeUndefined();
    expect(item.mean_nodes).toBeUndefined();
    expect(item.mean_backtracks).toBeUndefined();
    expect(item.mean_soft_penalty).toBeUndefined();
  });
});

describe("seriesFor", () => {
  it("groups points by num_sessions and calculates means for solved runs", () => {
    const rows: BenchmarkRow[] = [
      makeRow({ algorithm: "A", num_sessions: 30, runtime_s: 0.1, nodes: 100 }),
      makeRow({ algorithm: "A", num_sessions: 30, runtime_s: 0.2, nodes: 150 }),
      makeRow({ algorithm: "B", num_sessions: 30, runtime_s: 0.05, nodes: 40 }),
      makeRow({ algorithm: "A", num_sessions: 80, runtime_s: 1.5, nodes: 2000 }),
      makeRow({
        algorithm: "B",
        num_sessions: 80,
        status: "TIMEOUT",
        solved: false,
        valid: false,
        runtime_s: 10.0,
        nodes: 9999,
      }),
    ];

    const runtimeSeries = seriesFor("runtime_s", rows);
    expect(runtimeSeries).toHaveLength(2);
    const pt0 = runtimeSeries[0]!;
    const pt1 = runtimeSeries[1]!;
    expect(pt0.num_sessions).toBe(30);
    expect(pt0.A).toBeCloseTo(0.15);
    expect(pt0.B).toBeCloseTo(0.05);

    expect(pt1.num_sessions).toBe(80);
    expect(pt1.A).toBeCloseTo(1.5);
    // Unsolved B at 80 sessions should be omitted/undefined
    expect(pt1.B).toBeUndefined();

    const successSeries = seriesFor("successRate", rows);
    expect(successSeries).toHaveLength(2);
    const s0 = successSeries[0]!;
    const s1 = successSeries[1]!;
    expect(s0.A).toBe(100);
    expect(s0.B).toBe(100);
    expect(s1.A).toBe(100);
    expect(s1.B).toBe(0);
  });
});
