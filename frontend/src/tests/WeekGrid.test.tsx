import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { WeekGrid } from "../components/WeekGrid";
import type { Entry, GridDto } from "../api/types";

describe("WeekGrid Component", () => {
  const grid: GridDto = {
    day_names: ["Mon", "Tue", "Wed"],
    slot_starts: ["09:00", "10:00", "11:00"],
    slot_ends: ["10:00", "11:00", "12:00"],
  };

  const entries: Entry[] = [
    {
      session_id: "FAI|A|1",
      course_id: "FAI",
      course_name: "Intro to AI",
      teacher_id: "T1",
      teacher_name: "Dr. Smith",
      division_id: "A",
      division_name: "Div A",
      room_id: "R101",
      room_name: "Room 101",
      day: 0,
      day_name: "Mon",
      start_slot: 0,
      end_slot: 1,
      start_time: "09:00",
      end_time: "10:00",
      duration_slots: 1,
    },
    {
      session_id: "PLAB|A|1",
      course_id: "PLAB",
      course_name: "Physics Lab",
      teacher_id: "T2",
      teacher_name: "Prof. Einstein",
      division_id: "A",
      division_name: "Div A",
      room_id: "R102",
      room_name: "Lab 102",
      day: 1,
      day_name: "Tue",
      start_slot: 1,
      end_slot: 3,
      start_time: "10:00",
      end_time: "12:00",
      duration_slots: 2,
    },
  ];

  it("renders time headers, day headers, and course cards in blocks mode", () => {
    render(<WeekGrid entries={entries} grid={grid} visibleDays={[0, 1, 2]} />);

    expect(screen.getByText("Mon")).toBeInTheDocument();
    expect(screen.getByText("Tue")).toBeInTheDocument();
    expect(screen.getByText("Wed")).toBeInTheDocument();

    const timeMatches = screen.getAllByText("09:00–10:00");
    expect(timeMatches.length).toBeGreaterThanOrEqual(1);

    // Check course cards
    expect(screen.getByText("Intro to AI")).toBeInTheDocument();
    expect(screen.getByText("Physics Lab")).toBeInTheDocument();
    expect(screen.getByText("Dr. Smith")).toBeInTheDocument();
    expect(screen.getByText("Prof. Einstein")).toBeInTheDocument();

    // Verify 2-slot lab card indicates duration
    expect(screen.getByText("2 slots")).toBeInTheDocument();
  });

  it("renders detailed title tooltip for accessibility", () => {
    render(<WeekGrid entries={entries} grid={grid} visibleDays={[0, 1, 2]} />);

    const aiCard = screen.getByText("Intro to AI").closest(".weekgrid-card");
    expect(aiCard).toBeDefined();
    expect(aiCard).toHaveAttribute(
      "title",
      expect.stringContaining("Intro to AI (FAI)")
    );
    expect(aiCard).toHaveAttribute(
      "title",
      expect.stringContaining("Teacher: Dr. Smith (T1)")
    );
    expect(aiCard).toHaveAttribute(
      "title",
      expect.stringContaining("Room: Room 101 (R101)")
    );
  });

  it("switches to stacked mode when sessions overlap at the same day and slot", () => {
    const overlappingEntries: Entry[] = [
      entries[0],
      {
        session_id: "MATH|B|1",
        course_id: "MATH",
        course_name: "Discrete Math",
        teacher_id: "T3",
        teacher_name: "Dr. Euler",
        division_id: "B",
        division_name: "Div B",
        room_id: "R103",
        room_name: "Room 103",
        day: 0, // Same day
        day_name: "Mon",
        start_slot: 0, // Same slot!
        end_slot: 1,
        start_time: "09:00",
        end_time: "10:00",
        duration_slots: 1,
      },
    ];

    render(<WeekGrid entries={overlappingEntries} grid={grid} visibleDays={[0, 1, 2]} />);

    // In stacked mode, both overlapping entries should be visible
    expect(screen.getByText("Intro to AI")).toBeInTheDocument();
    expect(screen.getByText("Discrete Math")).toBeInTheDocument();
    expect(screen.getByText(/Dr\. Euler/)).toBeInTheDocument();
  });
});
