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

  it("renders time headers, day headers, and course cards", () => {
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
  });
});
