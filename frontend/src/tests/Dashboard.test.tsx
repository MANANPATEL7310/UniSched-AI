import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppProvider } from "../state/AppContext.js";
import { Dashboard } from "../pages/Dashboard.js";

describe("Dashboard page", () => {
  it("renders with nothing loaded without crashing and shows empty stat dashes", () => {
    localStorage.clear();
    render(
      <AppProvider>
        <Dashboard />
      </AppProvider>
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
});
