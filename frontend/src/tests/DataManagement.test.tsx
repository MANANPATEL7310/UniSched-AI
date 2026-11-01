import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AppProvider } from "../state/AppContext";
import { DataManagement } from "../pages/DataManagement";
import * as client from "../api/client";
import type { InstanceDraft, ValidateResponse } from "../api/types";

const mockTinyDraft: InstanceDraft = {
  name: "tiny",
  days: ["Mon", "Tue"],
  slots: [
    { start: "09:00", end: "10:00" },
    { start: "10:00", end: "11:00" },
  ],
  teachers: [
    {
      teacher_id: "T1",
      teacher_name: "Dr. Smith",
      unavailable_slots: [],
      preferred_slots: [],
      max_daily_sessions: null,
    },
  ],
  courses: [
    {
      course_id: "FAI",
      course_name: "Intro to AI",
      teacher_id: "T1",
      sessions_per_week: 2,
      duration_slots: 1,
      room_types: ["lecture"],
      eligible_divisions: ["A"],
    },
  ],
  divisions: [
    {
      division_id: "A",
      division_name: "Division A",
      student_count: 30,
      enrolled_courses: ["FAI"],
    },
  ],
  rooms: [
    {
      room_id: "R101",
      room_name: "Room 101",
      room_type: "lecture",
      capacity: 40,
      unavailable_slots: [],
    },
  ],
  fixed_assignments: [],
};

const mockValidateRes: ValidateResponse = {
  parse_error: null,
  issues: [],
  summary: {
    courses: 1,
    teachers: 1,
    rooms: 1,
    divisions: 1,
    sessions: 2,
  },
};

describe("DataManagement page", () => {
  it("renders source panel with 3 tabs and loads sample draft on button click", async () => {
    localStorage.clear();
    vi.spyOn(client, "listSamples").mockResolvedValue([
      { name: "tiny", description: "Tiny 5-session dataset" },
    ]);
    vi.spyOn(client, "getSample").mockResolvedValue(mockTinyDraft);
    vi.spyOn(client, "getPresets").mockResolvedValue({});
    vi.spyOn(client, "validateDraft").mockResolvedValue(mockValidateRes);

    render(
      <AppProvider>
        <DataManagement />
      </AppProvider>
    );

    // Initial state
    expect(screen.getByText("Data Management")).toBeInTheDocument();
    expect(screen.getByText("Sample Instance")).toBeInTheDocument();
    expect(screen.getByText("Upload CSV")).toBeInTheDocument();
    expect(screen.getByText("Random Generator")).toBeInTheDocument();

    await waitFor(() => {
      expect(client.listSamples).toHaveBeenCalled();
    });

    // Click Load Sample
    const loadBtn = screen.getByRole("button", { name: /Load Sample/i });
    fireEvent.click(loadBtn);

    await waitFor(() => {
      expect(client.getSample).toHaveBeenCalledWith("tiny");
    });

    // Verify Editor appears
    expect(screen.getByText(/2\. Edit Instance:/i)).toBeInTheDocument();
    expect(screen.getByText("Teachers (1)")).toBeInTheDocument();
    expect(screen.getByText("Courses (1)")).toBeInTheDocument();
    expect(screen.getByText("Divisions (1)")).toBeInTheDocument();
    expect(screen.getByText("Rooms (1)")).toBeInTheDocument();

    // Click Validate & Apply
    const validateBtn = screen.getByRole("button", { name: /Validate & Apply/i });
    fireEvent.click(validateBtn);

    await waitFor(() => {
      expect(client.validateDraft).toHaveBeenCalled();
    });

    // Verify accepted message in IssuesTable
    expect(
      screen.getByText("Data accepted: 2 sessions to schedule.")
    ).toBeInTheDocument();
  });
});
