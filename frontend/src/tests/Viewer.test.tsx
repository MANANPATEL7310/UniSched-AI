import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AppProvider } from "../state/AppContext";
import { Viewer } from "../pages/Viewer";

describe("Viewer Page", () => {
  it("renders empty state initially with fixture preview button", () => {
    localStorage.clear();
    render(
      <AppProvider>
        <Viewer />
      </AppProvider>
    );

    expect(screen.getByText("No Timetable Available")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Preview Sample Solution \(Tiny Fixture\)/i })
    ).toBeInTheDocument();
  });

  it("loads fixture outcome and displays timetable in calendar and table modes", () => {
    localStorage.clear();
    render(
      <AppProvider>
        <Viewer />
      </AppProvider>
    );

    // Click load fixture preview
    const previewBtn = screen.getByRole("button", {
      name: /Preview Sample Solution \(Tiny Fixture\)/i,
    });
    fireEvent.click(previewBtn);

    // Timetable should now be visible
    expect(screen.getByText(/✔ VALID/i)).toBeInTheDocument();
    expect(screen.getByText("View By:")).toBeInTheDocument();

    // In calendar mode, verify sessions appear (matching tiny_outcome.json)
    const faiMatches = screen.getAllByText("Foundation of AI");
    expect(faiMatches.length).toBeGreaterThanOrEqual(1);

    const labMatches = screen.getAllByText("Python Lab");
    expect(labMatches.length).toBeGreaterThanOrEqual(1);

    // Verify footer text
    expect(
      screen.getByText("This weekly timetable repeats every week of the semester.")
    ).toBeInTheDocument();

    // Switch to Table mode
    const tableModeBtn = screen.getByRole("button", { name: "Table" });
    fireEvent.click(tableModeBtn);

    // Check table headers
    expect(screen.getByText("Session ID")).toBeInTheDocument();
    expect(screen.getByText("Duration (slots)")).toBeInTheDocument();
  });
});
