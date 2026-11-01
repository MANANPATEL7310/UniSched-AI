import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { App } from "../App.js";
import * as client from "../api/client.js";

describe("App root component", () => {
  it("renders layout, sidebar navigation, and default Dashboard route", async () => {
    localStorage.clear();
    vi.spyOn(client, "health").mockResolvedValue({ status: "ok", version: "1.0" });

    render(<App />);

    // Sidebar branding
    expect(screen.getByText("Timetable CSP")).toBeInTheDocument();
    expect(screen.getByText("Fundamentals of AI")).toBeInTheDocument();

    // Navigation links
    expect(screen.getByRole("link", { name: /Dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Data Management/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Generate Timetable/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Timetable Viewer/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Constraint Validation/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Algorithm Comparison/i })).toBeInTheDocument();

    // Default route renders Dashboard
    expect(
      screen.getByText("Intelligent University Timetable Scheduler")
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(client.health).toHaveBeenCalled();
    });
  });
});
