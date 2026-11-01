import { describe, expect, it } from "vitest";
import { appReducer, canGenerate, type AppState } from "../state/reducer.js";
import type { InstanceDraft, RunOutcome } from "../api/types.js";

const mockDraft1: InstanceDraft = {
  name: "instance1",
  days: ["Mon"],
  slots: [{ start: "09:00", end: "10:00" }],
  teachers: [],
  courses: [],
  divisions: [],
  rooms: [],
  fixed_assignments: [],
};

const mockDraft2: InstanceDraft = {
  ...mockDraft1,
  name: "instance2",
};

const mockOutcome: RunOutcome = {
  run_id: "run-xyz",
  algorithm: "A",
  status: "SOLVED",
  message: "ok",
  is_valid: true,
  num_sessions: 2,
  metrics: {} as any,
  timetable: null,
  validation: null,
  soft: null,
};

describe("appReducer", () => {
  const stateWithResults: AppState = {
    draft: mockDraft1,
    applied: {
      draft: mockDraft1,
      summary: { courses: 1, teachers: 1, rooms: 1, divisions: 1, sessions: 2 },
      issues: [],
    },
    dirty: false,
    sourceLabel: "Sample: instance1",
    runId: "run-xyz",
    runAlgorithm: "A",
    outcome: mockOutcome,
    runError: { code: "ERR", message: "fail" },
    benchRows: null,
    benchMeta: null,
  };

  it("SET_DRAFT resets runId, outcome, and runError (Reset Rule)", () => {
    const next = appReducer(stateWithResults, {
      type: "SET_DRAFT",
      draft: mockDraft2,
      source: "Sample: instance2",
    });

    expect(next.draft).toEqual(mockDraft2);
    expect(next.sourceLabel).toBe("Sample: instance2");
    expect(next.applied).toBeNull();
    expect(next.dirty).toBe(false);
    expect(next.runId).toBeNull();
    expect(next.outcome).toBeNull();
    expect(next.runError).toBeNull();
    expect(next.runAlgorithm).toBeNull();
  });

  it("APPLY resets runId, outcome, and runError (Reset Rule) and clears dirty", () => {
    const stateEdited = {
      ...stateWithResults,
      dirty: true,
      draft: mockDraft2,
    };

    const next = appReducer(stateEdited, {
      type: "APPLY",
      applied: {
        draft: mockDraft2,
        summary: { courses: 2, teachers: 2, rooms: 2, divisions: 2, sessions: 4 },
        issues: [],
      },
    });

    expect(next.dirty).toBe(false);
    expect(next.applied?.draft).toEqual(mockDraft2);
    expect(next.runId).toBeNull();
    expect(next.outcome).toBeNull();
    expect(next.runError).toBeNull();
    expect(next.runAlgorithm).toBeNull();
  });

  it("EDIT_DRAFT updates draft and marks dirty = true", () => {
    const next = appReducer(stateWithResults, {
      type: "EDIT_DRAFT",
      draft: { ...mockDraft1, name: "edited" },
    });

    expect(next.dirty).toBe(true);
    expect(next.draft?.name).toBe("edited");
    // outcome remains untouched until apply/set_draft
    expect(next.outcome).toBe(mockOutcome);
  });

  it("RUN_STARTED sets runId and runAlgorithm and clears runError", () => {
    const s = { ...stateWithResults, runError: { code: "OLD", message: "old" } };
    const next = appReducer(s, {
      type: "RUN_STARTED",
      runId: "new-run",
      algorithm: "B",
    });

    expect(next.runId).toBe("new-run");
    expect(next.runAlgorithm).toBe("B");
    expect(next.runError).toBeNull();
  });

  it("RUN_FINISHED sets outcome and error", () => {
    const next = appReducer(stateWithResults, {
      type: "RUN_FINISHED",
      outcome: mockOutcome,
      error: null,
    });

    expect(next.outcome).toBe(mockOutcome);
    expect(next.runError).toBeNull();
  });

  it("RESET_RESULTS clears results", () => {
    const next = appReducer(stateWithResults, { type: "RESET_RESULTS" });
    expect(next.runId).toBeNull();
    expect(next.outcome).toBeNull();
    expect(next.runError).toBeNull();
  });
});

describe("canGenerate selector", () => {
  it("returns false if applied is null", () => {
    const s: AppState = {
      draft: mockDraft1,
      applied: null,
      dirty: false,
      sourceLabel: "test",
      runId: null,
      runAlgorithm: null,
      outcome: null,
      runError: null,
      benchRows: null,
      benchMeta: null,
    };
    expect(canGenerate(s)).toBe(false);
  });

  it("returns false if dirty is true", () => {
    const s: AppState = {
      draft: mockDraft1,
      applied: {
        draft: mockDraft1,
        summary: { courses: 1, teachers: 1, rooms: 1, divisions: 1, sessions: 1 },
        issues: [],
      },
      dirty: true,
      sourceLabel: "test",
      runId: null,
      runAlgorithm: null,
      outcome: null,
      runError: null,
      benchRows: null,
      benchMeta: null,
    };
    expect(canGenerate(s)).toBe(false);
  });

  it("returns false if applied has ERROR issues", () => {
    const s: AppState = {
      draft: mockDraft1,
      applied: {
        draft: mockDraft1,
        summary: { courses: 1, teachers: 1, rooms: 1, divisions: 1, sessions: 1 },
        issues: [{ severity: "ERROR", code: "UNKNOWN_TEACHER", message: "bad", entity: null }],
      },
      dirty: false,
      sourceLabel: "test",
      runId: null,
      runAlgorithm: null,
      outcome: null,
      runError: null,
      benchRows: null,
      benchMeta: null,
    };
    expect(canGenerate(s)).toBe(false);
  });

  it("returns true if applied exists, not dirty, and only WARNING issues", () => {
    const s: AppState = {
      draft: mockDraft1,
      applied: {
        draft: mockDraft1,
        summary: { courses: 1, teachers: 1, rooms: 1, divisions: 1, sessions: 1 },
        issues: [{ severity: "WARNING", code: "TIGHT_SCHEDULE", message: "tight", entity: null }],
      },
      dirty: false,
      sourceLabel: "test",
      runId: null,
      runAlgorithm: null,
      outcome: null,
      runError: null,
      benchRows: null,
      benchMeta: null,
    };
    expect(canGenerate(s)).toBe(true);
  });
});
