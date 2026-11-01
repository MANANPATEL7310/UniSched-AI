import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Generate } from "../pages/Generate";
import { AppContext, type AppContextValue } from "../state/AppContext";
import type { AppState } from "../state/reducer";
import * as client from "../api/client";
import tinyOutcome from "./fixtures/tiny_outcome.json";
import type { RunOutcome } from "../api/types";

vi.mock("../api/client", () => ({
  startRun: vi.fn(),
  cancelRun: vi.fn(),
  getRun: vi.fn(),
}));

function makeContextValue(stateOverrides?: Partial<AppState>, canGen = false): AppContextValue {
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
    dispatch: vi.fn(),
    canGenerate: canGen,
  };
}

describe("Generate page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows disabled banner and controls when canGenerate is false", () => {
    const ctx = makeContextValue({ applied: null }, false);

    render(
      <MemoryRouter>
        <AppContext.Provider value={ctx}>
          <Generate />
        </AppContext.Provider>
      </MemoryRouter>
    );

    expect(screen.getByText("Cannot Start Solver:")).toBeInTheDocument();
    expect(
      screen.getByText("No dataset has been applied yet. Load or enter curriculum data in Data Management.")
    ).toBeInTheDocument();

    const generateBtn = screen.getByRole("button", { name: "Generate Timetable" });
    expect(generateBtn).toBeDisabled();
  });

  it("renders all 4 algorithm cards and allows selecting them", () => {
    const ctx = makeContextValue(
      {
        applied: {
          draft: {} as any,
          summary: { sessions: 5 } as any,
          issues: [],
        },
      },
      true
    );

    render(
      <MemoryRouter>
        <AppContext.Provider value={ctx}>
          <Generate />
        </AppContext.Provider>
      </MemoryRouter>
    );

    expect(screen.getByText("Config A: Baseline Backtracking")).toBeInTheDocument();
    expect(screen.getByText("Config B: MRV + Degree + LCV")).toBeInTheDocument();
    expect(screen.getByText("Config C: Forward Checking")).toBeInTheDocument();
    expect(screen.getByText("Config D: AC-3 + MAC")).toBeInTheDocument();

    // Click Config B
    const cardB = screen.getByText("Config B: MRV + Degree + LCV").closest(".algo-card");
    expect(cardB).toBeDefined();
    fireEvent.click(cardB!);

    expect(cardB).toHaveClass("selected");
  });

  it("initiates run and calls startRun when Generate is clicked", async () => {
    vi.mocked(client.startRun).mockResolvedValueOnce({ run_id: "run-123" });

    const ctx = makeContextValue(
      {
        applied: {
          draft: { days: ["Monday"] } as any,
          summary: { sessions: 5 } as any,
          issues: [],
        },
      },
      true
    );

    render(
      <MemoryRouter>
        <AppContext.Provider value={ctx}>
          <Generate />
        </AppContext.Provider>
      </MemoryRouter>
    );

    const generateBtn = screen.getByRole("button", { name: "Generate Timetable" });
    expect(generateBtn).not.toBeDisabled();

    fireEvent.click(generateBtn);

    expect(client.startRun).toHaveBeenCalledWith(
      { days: ["Monday"] },
      { algorithm: "A", timeout_s: 60, node_limit: null }
    );
  });

  it("renders progress panel and cancel button when run is in progress", () => {
    const ctx = makeContextValue(
      {
        runId: "active-run-1",
        runAlgorithm: "B",
        outcome: null,
      },
      true
    );

    render(
      <MemoryRouter>
        <AppContext.Provider value={ctx}>
          <Generate />
        </AppContext.Provider>
      </MemoryRouter>
    );

    expect(screen.getByTestId("progress-panel")).toBeInTheDocument();
    expect(screen.getByText("Search in Progress (Config B)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel Search" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cancel Search" }));
    expect(client.cancelRun).toHaveBeenCalledWith("active-run-1");
  });

  it("renders result panel, metrics, and explanation when outcome is present", () => {
    const ctx = makeContextValue(
      {
        outcome: tinyOutcome as unknown as RunOutcome,
      },
      true
    );

    render(
      <MemoryRouter>
        <AppContext.Provider value={ctx}>
          <Generate />
        </AppContext.Provider>
      </MemoryRouter>
    );

    expect(screen.getByTestId("result-panel")).toBeInTheDocument();
    expect(screen.getByText("Run Outcome: Config A")).toBeInTheDocument();
    expect(screen.getByText("Explain this run")).toBeInTheDocument();
    expect(screen.getByText(/The scheduler had 5 sessions to place/)).toBeInTheDocument();

    expect(screen.getByRole("button", { name: "Open Timetable Viewer" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open Constraint Validation" })).toBeInTheDocument();
  });
});
