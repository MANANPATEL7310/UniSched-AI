import { describe, expect, it } from "vitest";
import type { AppState } from "../state/reducer.js";
import { deriveStatus } from "../lib/status.js";
import type { InstanceDraft, RunOutcome } from "../api/types.js";

const mockDraft: InstanceDraft = {
  name: "test",
  days: ["Mon"],
  slots: [{ start: "09:00", end: "10:00" }],
  teachers: [],
  courses: [],
  divisions: [],
  rooms: [],
  fixed_assignments: [],
};

const mockOutcome: RunOutcome = {
  run_id: "run-1",
  algorithm: "A",
  status: "SOLVED",
  message: "Found timetable",
  is_valid: true,
  num_sessions: 5,
  metrics: {
    nodes: 10,
    attempts: 10,
    backtracks: 0,
    checks: 15,
    values_pruned: 0,
    root_pruned: 0,
    domain_wipeouts: 0,
    runtime_s: 0.05,
    build_s: 0.01,
    peak_memory_kb: null,
  },
  timetable: null,
  validation: {
    is_valid: true,
    sessions_required: 5,
    sessions_assigned: 5,
    counts_by_type: {} as any,
    violations: [],
  },
  soft: null,
};

function baseState(): AppState {
  return {
    draft: mockDraft,
    applied: {
      draft: mockDraft,
      summary: { courses: 1, teachers: 1, rooms: 1, divisions: 1, sessions: 5 },
      issues: [],
    },
    dirty: false,
    sourceLabel: "Sample: test",
    runId: null,
    runAlgorithm: null,
    outcome: null,
    runError: null,
    benchRows: null,
    benchMeta: null,
  };
}

describe("deriveStatus", () => {
  it("derives NO_DATA when draft is null", () => {
    const s = { ...baseState(), draft: null };
    const res = deriveStatus(s, false);
    expect(res.code).toBe("NO_DATA");
    expect(res.tone).toBe("grey");
    expect(res.text).toBe("No data loaded.");
  });

  it("derives UNAPPLIED when dirty or applied is null", () => {
    const s1 = { ...baseState(), dirty: true };
    expect(deriveStatus(s1, false).code).toBe("UNAPPLIED");

    const s2 = { ...baseState(), applied: null };
    expect(deriveStatus(s2, false).code).toBe("UNAPPLIED");
  });

  it("derives INPUT_ERRORS when applied issues contain ERROR", () => {
    const s = {
      ...baseState(),
      applied: {
        ...baseState().applied!,
        issues: [
          { severity: "ERROR" as const, code: "DUP_ID", message: "Duplicate id", entity: null },
          { severity: "WARNING" as const, code: "TIGHT", message: "Tight", entity: null },
        ],
      },
    };
    const res = deriveStatus(s, false);
    expect(res.code).toBe("INPUT_ERRORS");
    expect(res.tone).toBe("red");
    expect(res.text).toContain("1 error(s)");
  });

  it("derives RUNNING when running is true", () => {
    const s = baseState();
    const res = deriveStatus(s, true);
    expect(res.code).toBe("RUNNING");
    expect(res.tone).toBe("blue");
    expect(res.text).toBe("Search in progress…");
  });

  it("derives ERROR when runError is present", () => {
    const s = {
      ...baseState(),
      runError: { code: "INTERNAL", message: "Crashed" },
    };
    const res = deriveStatus(s, false);
    expect(res.code).toBe("ERROR");
    expect(res.tone).toBe("red");
    expect(res.text).toBe("Unexpected error: Crashed");
  });

  it("derives READY when outcome is null", () => {
    const s = baseState();
    const res = deriveStatus(s, false);
    expect(res.code).toBe("READY");
    expect(res.tone).toBe("blue");
    expect(res.text).toBe("Ready to generate.");
  });

  it("derives VALID when outcome is_valid is true", () => {
    const s = { ...baseState(), outcome: mockOutcome };
    const res = deriveStatus(s, false);
    expect(res.code).toBe("VALID");
    expect(res.tone).toBe("green");
    expect(res.text).toBe(
      "Valid timetable: 0 hard-constraint violations, all 5 sessions scheduled."
    );
  });

  it("derives INVALID when status is SOLVED but is_valid is false", () => {
    const s = {
      ...baseState(),
      outcome: {
        ...mockOutcome,
        is_valid: false,
        validation: {
          ...mockOutcome.validation!,
          is_valid: false,
          violations: [
            {
              type: "ROOM_CONFLICT" as const,
              session_ids: ["s1", "s2"],
              resource: "R1",
              day: 0,
              slot: 0,
              explanation: "Room overlap",
            },
          ],
        },
      },
    };
    const res = deriveStatus(s, false);
    expect(res.code).toBe("INVALID");
    expect(res.tone).toBe("red");
    expect(res.text).toBe(
      "The solver returned a timetable but the independent validator found 1 violation(s). Do not use it."
    );
  });

  it("derives INFEASIBLE when INFEASIBLE_PROVEN", () => {
    const s = {
      ...baseState(),
      outcome: {
        ...mockOutcome,
        is_valid: false,
        status: "INFEASIBLE_PROVEN" as const,
        message: "Backtracked completely.",
      },
    };
    const res = deriveStatus(s, false);
    expect(res.code).toBe("INFEASIBLE");
    expect(res.tone).toBe("orange");
    expect(res.text).toContain("No valid timetable exists");
  });

  it("derives TIMEOUT when status is TIMEOUT", () => {
    const s = {
      ...baseState(),
      outcome: {
        ...mockOutcome,
        is_valid: false,
        status: "TIMEOUT" as const,
      },
    };
    const res = deriveStatus(s, false);
    expect(res.code).toBe("TIMEOUT");
    expect(res.tone).toBe("yellow");
    expect(res.text).toContain("Time limit reached");
  });

  it("derives NODE_LIMIT when status is NODE_LIMIT", () => {
    const s = {
      ...baseState(),
      outcome: {
        ...mockOutcome,
        is_valid: false,
        status: "NODE_LIMIT" as const,
      },
    };
    const res = deriveStatus(s, false);
    expect(res.code).toBe("NODE_LIMIT");
    expect(res.tone).toBe("yellow");
    expect(res.text).toBe("Node limit reached. This does NOT prove infeasibility.");
  });

  it("derives CANCELLED when status is CANCELLED", () => {
    const s = {
      ...baseState(),
      outcome: {
        ...mockOutcome,
        is_valid: false,
        status: "CANCELLED" as const,
      },
    };
    const res = deriveStatus(s, false);
    expect(res.code).toBe("CANCELLED");
    expect(res.tone).toBe("grey");
    expect(res.text).toBe("Search cancelled.");
  });
});
