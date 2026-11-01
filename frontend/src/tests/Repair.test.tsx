import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppProvider, useApp } from "../state/AppContext.js";
import { Repair } from "../pages/Repair.js";
import * as client from "../api/client.js";
import tinyOutcome from "./fixtures/tiny_outcome.json";

function SeededRepair() {
  const { dispatch } = useApp();

  return (
    <div>
      <button
        type="button"
        onClick={() => {
          const draft = {
            name: "tiny",
            days: ["Mon", "Tue"],
            slots: [
              { start: "09:00", end: "10:00" },
              { start: "10:00", end: "11:00" },
              { start: "11:00", end: "12:00" },
            ],
            teachers: [
              {
                teacher_id: "T1",
                teacher_name: "Prof Alice",
                unavailable_slots: [],
                preferred_slots: [],
                max_daily_sessions: null,
              },
            ],
            courses: [
              {
                course_id: "C1",
                course_name: "AI",
                teacher_id: "T1",
                sessions_per_week: 1,
                duration_slots: 1,
                room_types: ["lecture" as const],
                eligible_divisions: ["D1"],
              },
            ],
            divisions: [
              {
                division_id: "D1",
                division_name: "Div A",
                student_count: 30,
                enrolled_courses: ["C1"],
              },
            ],
            rooms: [
              {
                room_id: "R101",
                room_name: "Room 101",
                room_type: "lecture" as const,
                capacity: 50,
                unavailable_slots: [],
              },
            ],
            fixed_assignments: [],
          };
          dispatch({ type: "SET_DRAFT", draft, source: "test" });
          dispatch({
            type: "RUN_FINISHED",
            outcome: tinyOutcome as any,
            error: null,
          });
        }}
      >
        Seed Data
      </button>
      <Repair />
    </div>
  );
}

describe("Repair Page", () => {
  it("renders empty state message when no published timetable exists", () => {
    localStorage.clear();
    render(
      <AppProvider>
        <MemoryRouter>
          <Repair />
        </MemoryRouter>
      </AppProvider>
    );

    expect(screen.getByText("No published timetable found in current session.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Go to Generate Page/i })).toBeInTheDocument();
  });

  it("renders controls and performs repair when seeded", async () => {
    localStorage.clear();
    const repairSpy = vi.spyOn(client, "repair").mockResolvedValue({
      status: "SOLVED",
      outcome: tinyOutcome as any,
      diff: [
        {
          session_id: "C1|D1|1",
          course_name: "AI",
          division_name: "Div A",
          teacher_name: "Prof Alice",
          old_day: 0,
          old_slot: 0,
          old_room_id: "R101",
          new_day: 0,
          new_slot: 1,
          new_room_id: "R101",
          change_type: "MOVED_SLOT",
        },
      ],
      relaxed_locks: [],
      change_penalty: 1,
      message: "Repaired successfully with minimal change.",
    });

    render(
      <AppProvider>
        <MemoryRouter>
          <SeededRepair />
        </MemoryRouter>
      </AppProvider>
    );

    // Seed data
    fireEvent.click(screen.getByText("Seed Data"));

    // Check headings and controls
    expect(screen.getByText("Timetable Repair & Rescheduling")).toBeInTheDocument();
    expect(screen.getByText("1. Inject Unavailability Disruption")).toBeInTheDocument();
    expect(screen.getByText("2. Locking Policy & Repair Actions")).toBeInTheDocument();

    const repairBtn = screen.getByRole("button", { name: /⚡ Repair Timetable/i });
    expect(repairBtn).toBeInTheDocument();

    // Trigger repair
    fireEvent.click(repairBtn);

    await waitFor(() => {
      expect(repairSpy).toHaveBeenCalled();
      expect(screen.getByText(/Repair Outcome: SOLVED/i)).toBeInTheDocument();
      expect(screen.getByText(/Assignments Changed:/i)).toBeInTheDocument();
      expect(screen.getByText("MOVED_SLOT")).toBeInTheDocument();
    });

    // Check publish button
    const publishBtn = screen.getByRole("button", { name: /✓ Publish Revised Timetable/i });
    expect(publishBtn).toBeInTheDocument();
    fireEvent.click(publishBtn);

    expect(screen.getByText(/Revised timetable published successfully!/i)).toBeInTheDocument();
    repairSpy.mockRestore();
  });
});

