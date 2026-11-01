import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { IssuesTable } from "../components/IssuesTable";
import type { InputIssue } from "../api/types";

describe("IssuesTable", () => {
  it("renders parse error banner when parseError is provided", () => {
    render(<IssuesTable issues={[]} parseError="Syntax error in rooms.csv" />);
    expect(screen.getByText("Syntax error in rooms.csv")).toBeInTheDocument();
  });

  it("renders error banner when ERROR severity issue exists", () => {
    const issues: InputIssue[] = [
      { severity: "ERROR", code: "UNKNOWN_TEACHER", entity: "MATH", message: "Teacher T99 not found" },
      { severity: "WARNING", code: "TIGHT_SCHEDULE", entity: "Div A", message: "Schedule is tight" },
    ];

    render(<IssuesTable issues={issues} />);
    expect(
      screen.getByText(/Input has 1 error\(s\)\. Fix these errors before generating\./i)
    ).toBeInTheDocument();
    expect(screen.getByText("UNKNOWN_TEACHER")).toBeInTheDocument();
    expect(screen.getByText("Teacher T99 not found")).toBeInTheDocument();
  });

  it("renders green accepted banner when issues list has 0 errors and sessionsCount is provided", () => {
    render(<IssuesTable issues={[]} sessionsCount={15} />);
    expect(
      screen.getByText("Data accepted: 15 sessions to schedule.")
    ).toBeInTheDocument();
  });
});
