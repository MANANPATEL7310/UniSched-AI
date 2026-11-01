import { describe, it, expect } from "vitest";
import { explainRun, ALGORITHM_OPTIONS } from "../lib/explanations";
import type { RunOutcome } from "../api/types";

function createDummyOutcome(overrides?: Partial<RunOutcome>): RunOutcome {
  return {
    run_id: "test-run",
    algorithm: "A",
    status: "SOLVED",
    message: "",
    is_valid: true,
    num_sessions: 12,
    metrics: {
      nodes: 50,
      attempts: 80,
      backtracks: 30,
      checks: 200,
      values_pruned: 15,
      root_pruned: 4,
      domain_wipeouts: 3,
      runtime_s: 0.125,
      build_s: 0.01,
      peak_memory_kb: null,
    },
    timetable: null,
    validation: null,
    soft: null,
    ...overrides,
  };
}

describe("explanations module", () => {
  it("defines all 4 algorithm cards A through D", () => {
    expect(ALGORITHM_OPTIONS).toHaveLength(4);
    expect(ALGORITHM_OPTIONS.map((a) => a.code)).toEqual(["A", "B", "C", "D"]);
  });

  it("explains baseline algorithm A runs", () => {
    const outcome = createDummyOutcome({ algorithm: "A", status: "SOLVED" });
    const sentences = explainRun(outcome);

    expect(sentences.length).toBeGreaterThanOrEqual(2);
    expect(sentences[0]).toContain("The scheduler had 12 sessions to place.");
    expect(sentences[0]).toContain("tried 80 candidate assignments and undid 30 of them");
    expect(sentences.some((s) => s.includes("MRV"))).toBe(false);
  });

  it("explains heuristic algorithm B runs", () => {
    const outcome = createDummyOutcome({ algorithm: "B", status: "SOLVED" });
    const sentences = explainRun(outcome);

    expect(sentences.some((s) => s.includes("MRV"))).toBe(true);
    expect(sentences.some((s) => s.includes("Degree"))).toBe(true);
  });

  it("explains forward checking algorithm C runs", () => {
    const outcome = createDummyOutcome({ algorithm: "C", status: "SOLVED" });
    const sentences = explainRun(outcome);

    expect(sentences.some((s) => s.includes("Forward checking removed 15 values"))).toBe(true);
    expect(sentences.some((s) => s.includes("dead end 3 times"))).toBe(true);
  });

  it("explains arc consistency algorithm D runs", () => {
    const outcome = createDummyOutcome({ algorithm: "D", status: "SOLVED" });
    const sentences = explainRun(outcome);

    expect(sentences.some((s) => s.includes("AC-3 removed 4 values"))).toBe(true);
    expect(sentences.some((s) => s.includes("MAC"))).toBe(true);
  });

  it("explains timeout and infeasible statuses correctly", () => {
    const timeoutOutcome = createDummyOutcome({ status: "TIMEOUT" });
    const timeoutSentences = explainRun(timeoutOutcome);
    expect(timeoutSentences.some((s) => s.includes("Time limit reached"))).toBe(true);
    expect(timeoutSentences.some((s) => s.includes("does NOT prove the problem is infeasible"))).toBe(true);

    const infeasibleOutcome = createDummyOutcome({ status: "INFEASIBLE_PROVEN" });
    const infeasibleSentences = explainRun(infeasibleOutcome);
    expect(infeasibleSentences.some((s) => s.includes("No valid timetable exists"))).toBe(true);
  });
});

