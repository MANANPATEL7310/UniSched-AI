import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppContext, type AppContextValue } from "../state/AppContext.js";
import { Dashboard } from "../pages/Dashboard.js";
import type { AppState } from "../state/reducer.js";
import type { RunOutcome } from "../api/types.js";
import tinyOutcome from "./fixtures/tiny_outcome.json";

function makeContextValue(stateOverrides?: Partial<AppState>): AppContextValue {
  const baseState: AppState = {
    draft: null,
    applied: null,
    dirty: false,
    sourceLabel: "None",
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

describe("Dashboard page", () => {
  it("renders with nothing loaded without crashing and shows empty stat dashes", () => {
    const ctx = makeContextValue();
    render(
      <AppContext.Provider value={ctx}>
        <Dashboard />
      </AppContext.Provider>
    );

    expect(
      screen.getByText("Intelligent University Timetable Scheduler")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Constraint Satisfaction: backtracking/i)
    ).toBeInTheDocument();
    expect(screen.getByText("No data loaded.")).toBeInTheDocument();

    // Check that stat cards render with "—"
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBe(5);

    // Check that FAI details exist
    expect(
      screen.getByText("About this project / FAI concepts")
    ).toBeInTheDocument();
  });

  it("renders stat cards from applied summary", () => {
    const ctx = makeContextValue({
      applied: {
        draft: {} as any,
        summary: {
          courses: 8,
          teachers: 5,
          rooms: 4,
          divisions: 3,
          sessions: 18,
        },
        issues: [],
      },
    });

    render(
      <AppContext.Provider value={ctx}>
        <Dashboard />
      </AppContext.Provider>
    );

    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("18")).toBeInTheDocument();
  });

  it("renders latest search result card and complete FAI concepts panel", () => {
    const ctx = makeContextValue({
      outcome: tinyOutcome as unknown as RunOutcome,
    });

    render(
      <AppContext.Provider value={ctx}>
        <Dashboard />
      </AppContext.Provider>
    );

    // Search Result Panel
    expect(screen.getByText("Latest Search Result")).toBeInTheDocument();
    expect(screen.getByText("Config A")).toBeInTheDocument();
    expect(screen.getByText("SOLVED")).toBeInTheDocument();
    expect(screen.getByText("✔ VALID")).toBeInTheDocument();

    // FAI Concepts
    expect(screen.getByText(/PEAS Task Environment/i)).toBeInTheDocument();
    expect(screen.getByText(/Fully Observable:/i)).toBeInTheDocument();
    expect(screen.getByText(/Deterministic:/i)).toBeInTheDocument();
    expect(screen.getByText(/Static:/i)).toBeInTheDocument();
    expect(screen.getByText(/Discrete:/i)).toBeInTheDocument();
    expect(screen.getByText(/Single-Agent:/i)).toBeInTheDocument();
    expect(screen.getByText(/Sequential \/ Episodic:/i)).toBeInTheDocument();

    expect(screen.getByText(/State-Space Formulation/i)).toBeInTheDocument();
    expect(screen.getByText(/Initial State:/i)).toBeInTheDocument();
    expect(screen.getByText(/Goal Test:/i)).toBeInTheDocument();

    expect(screen.getByText(/Constraint Satisfaction Formulation: CSP = \(X, D, C\)/i)).toBeInTheDocument();
    expect(screen.getByText(/No machine learning is used — classical symbolic constraint satisfaction/i)).toBeInTheDocument();
  });
});
