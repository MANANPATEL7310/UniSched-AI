import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBanner } from "../components/StatusBanner";
import { AppContext, type AppContextValue } from "../state/AppContext";
import type { AppState } from "../state/reducer";
import type { StatusInfo } from "../lib/status";

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

describe("StatusBanner component", () => {
  it("renders with role=status and aria-live=polite for screen readers", () => {
    const ctx = makeContextValue();
    render(
      <AppContext.Provider value={ctx}>
        <StatusBanner />
      </AppContext.Provider>
    );

    const banner = screen.getByRole("status");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveAttribute("aria-live", "polite");
    expect(banner).toHaveClass("tone-grey");
    expect(banner).toHaveTextContent("No data loaded.");
  });

  it("renders explicit StatusInfo prop when provided", () => {
    const customInfo: StatusInfo = {
      code: "VALID",
      tone: "green",
      text: "Timetable verified conflict-free.",
    };

    const ctx = makeContextValue();
    render(
      <AppContext.Provider value={ctx}>
        <StatusBanner info={customInfo} />
      </AppContext.Provider>
    );

    const banner = screen.getByRole("status");
    expect(banner).toHaveClass("tone-green");
    expect(banner).toHaveTextContent("✔");
    expect(banner).toHaveTextContent("Timetable verified conflict-free.");
  });

  it("renders tone-blue and running state when running=true", () => {
    const ctx = makeContextValue({
      draft: {} as any,
      dirty: false,
      applied: {
        draft: {} as any,
        summary: { sessions: 5 } as any,
        issues: [],
      },
    });
    render(
      <AppContext.Provider value={ctx}>
        <StatusBanner running={true} />
      </AppContext.Provider>
    );

    const banner = screen.getByRole("status");
    expect(banner).toHaveClass("tone-blue");
    expect(banner).toHaveTextContent("⏳");
    expect(banner).toHaveTextContent("Search in progress…");
  });

  it("renders tone-red for invalid outcome", () => {
    const invalidInfo: StatusInfo = {
      code: "INVALID",
      tone: "red",
      text: "Timetable has hard violations.",
    };

    const ctx = makeContextValue();
    render(
      <AppContext.Provider value={ctx}>
        <StatusBanner info={invalidInfo} />
      </AppContext.Provider>
    );

    const banner = screen.getByRole("status");
    expect(banner).toHaveClass("tone-red");
    expect(banner).toHaveTextContent("✖");
    expect(banner).toHaveTextContent("Timetable has hard violations.");
  });

  it("renders tone-yellow for timeout", () => {
    const timeoutInfo: StatusInfo = {
      code: "TIMEOUT",
      tone: "yellow",
      text: "Time limit reached after 60 s.",
    };

    const ctx = makeContextValue();
    render(
      <AppContext.Provider value={ctx}>
        <StatusBanner info={timeoutInfo} />
      </AppContext.Provider>
    );

    const banner = screen.getByRole("status");
    expect(banner).toHaveClass("tone-yellow");
    expect(banner).toHaveTextContent("⚠");
    expect(banner).toHaveTextContent("Time limit reached after 60 s.");
  });

  it("renders tone-orange for infeasible proven", () => {
    const infeasibleInfo: StatusInfo = {
      code: "INFEASIBLE",
      tone: "orange",
      text: "No valid timetable exists.",
    };

    const ctx = makeContextValue();
    render(
      <AppContext.Provider value={ctx}>
        <StatusBanner info={infeasibleInfo} />
      </AppContext.Provider>
    );

    const banner = screen.getByRole("status");
    expect(banner).toHaveClass("tone-orange");
    expect(banner).toHaveTextContent("⊘");
    expect(banner).toHaveTextContent("No valid timetable exists.");
  });
});
