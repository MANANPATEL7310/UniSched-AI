import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { Validation } from "../pages/Validation";
import { AppContext, type AppContextValue } from "../state/AppContext";
import type { AppState } from "../state/reducer";
import type { RunOutcome } from "../api/types";
import tinyOutcome from "./fixtures/tiny_outcome.json";

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

describe("Validation page", () => {
  it("renders empty state when no validation report is available", () => {
    const ctx = makeContextValue({ outcome: null });

    render(
      <AppContext.Provider value={ctx}>
        <Validation />
      </AppContext.Provider>
    );

    expect(screen.getByText("No Validation Report Yet")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Preview Sample Validation" })
    ).toBeInTheDocument();
  });

  it("renders VALID badge, caption, stats, and all 12 categories with zeros on valid sample", () => {
    const ctx = makeContextValue({
      outcome: tinyOutcome as unknown as RunOutcome,
    });

    render(
      <AppContext.Provider value={ctx}>
        <Validation />
      </AppContext.Provider>
    );

    // 1. Caption requirement
    expect(
      screen.getByText(
        "Checked by an independent validator that does not use the search code."
      )
    ).toBeInTheDocument();

    // 2. Big badge
    const badge = screen.getByTestId("validation-badge");
    expect(badge).toHaveTextContent("VALID");
    expect(badge).not.toHaveTextContent("NOT VALID");
    expect(badge).toHaveClass("badge-valid");

    // 3. Three stat cards
    expect(screen.getByText("Sessions Required")).toBeInTheDocument();
    expect(screen.getByText("Sessions Assigned")).toBeInTheDocument();
    expect(screen.getByText("Total Hard Violations")).toBeInTheDocument();

    // 4. All 12 categories in exact order
    const expectedCategories = [
      "Teacher conflicts",
      "Division conflicts",
      "Room conflicts",
      "Capacity",
      "Room type",
      "Teacher availability",
      "Room availability",
      "Duration / out of range",
      "Missing sessions",
      "Duplicate sessions",
      "Unknown sessions/rooms",
      "Fixed assignments",
    ];

    const catTable = screen.getByTestId("categories-table");
    const rows = within(catTable).getAllByRole("row").slice(1); // skip thead
    expect(rows).toHaveLength(12);

    expectedCategories.forEach((catName, idx) => {
      const row = rows[idx];
      expect(row).toBeDefined();
      expect(within(row!).getByText(catName)).toBeInTheDocument();
      // Status is Passed (0)
      expect(within(row!).getByText("Passed (0)")).toBeInTheDocument();
      expect(within(row!).getByText(String(idx + 1))).toBeInTheDocument();
    });

    // 5. Zero violations state
    expect(
      screen.getByText("✓ All Hard Constraints Satisfied")
    ).toBeInTheDocument();
  });

  it("renders NOT VALID badge and details table when violations exist", () => {
    const invalidOutcome: RunOutcome = {
      run_id: "test-invalid-1",
      algorithm: "A",
      status: "INFEASIBLE_PROVEN",
      message: "Hard constraints violated",
      is_valid: false,
      num_sessions: 5,
      metrics: {
        nodes: 10,
        attempts: 10,
        backtracks: 5,
        checks: 20,
        values_pruned: 0,
        root_pruned: 0,
        domain_wipeouts: 1,
        runtime_s: 0.05,
        build_s: 0.01,
        peak_memory_kb: null,
      },
      timetable: null,
      validation: {
        is_valid: false,
        sessions_required: 5,
        sessions_assigned: 4,
        counts_by_type: {
          MISSING_SESSION: 1,
          DUPLICATE_SESSION: 0,
          UNKNOWN_SESSION: 0,
          TEACHER_CONFLICT: 1,
          DIVISION_CONFLICT: 0,
          ROOM_CONFLICT: 0,
          CAPACITY: 0,
          ROOM_TYPE: 0,
          TEACHER_UNAVAILABLE: 0,
          ROOM_UNAVAILABLE: 0,
          DURATION: 0,
          OUT_OF_RANGE: 0,
          UNKNOWN_ROOM: 0,
          FIXED_ASSIGNMENT: 0,
        },
        violations: [
          {
            type: "TEACHER_CONFLICT",
            session_ids: ["S1", "S2"],
            resource: "T1",
            day: 0,
            slot: 1,
            explanation: "Teacher T1 assigned to S1 and S2 at the same time.",
          },
          {
            type: "MISSING_SESSION",
            session_ids: ["S5"],
            resource: null,
            day: null,
            slot: null,
            explanation: "Session S5 was not scheduled.",
          },
        ],
      },
      soft: null,
    };

    const ctx = makeContextValue({ outcome: invalidOutcome });

    render(
      <AppContext.Provider value={ctx}>
        <Validation />
      </AppContext.Provider>
    );

    // 1. NOT VALID badge
    const badge = screen.getByTestId("validation-badge");
    expect(badge).toHaveTextContent("NOT VALID");
    expect(badge).toHaveClass("badge-invalid");

    // 2. Violated buttons on table (Teacher conflicts and Missing sessions each have 1)
    expect(screen.getAllByRole("button", { name: "Violated (1)" })).toHaveLength(2);

    // 3. Violations details table
    const violTable = screen.getByTestId("violations-table");
    expect(within(violTable).getByText("TEACHER_CONFLICT")).toBeInTheDocument();
    expect(within(violTable).getByText("MISSING_SESSION")).toBeInTheDocument();
    expect(
      within(violTable).getByText("Teacher T1 assigned to S1 and S2 at the same time.")
    ).toBeInTheDocument();
    expect(within(violTable).getByText("Session S5 was not scheduled.")).toBeInTheDocument();

    // 4. Filter dropdown
    const filterSelect = screen.getByLabelText("Filter:");
    fireEvent.change(filterSelect, { target: { value: "teacher_conflicts" } });

    // After filtering by teacher_conflicts, only TEACHER_CONFLICT is visible
    expect(within(violTable).getByText("TEACHER_CONFLICT")).toBeInTheDocument();
    expect(within(violTable).queryByText("MISSING_SESSION")).not.toBeInTheDocument();
  });
});
