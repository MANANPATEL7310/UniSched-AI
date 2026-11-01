import { describe, expect, it } from "vitest";
import { entriesToCsv, escapeCsvField } from "../lib/csv.js";
import type { Entry } from "../api/types.js";

describe("csv library", () => {
  it("escapes fields correctly per RFC 4180", () => {
    expect(escapeCsvField("Simple")).toBe("Simple");
    expect(escapeCsvField("With,Comma")).toBe('"With,Comma"');
    expect(escapeCsvField('With"Quote')).toBe('"With""Quote"');
    expect(escapeCsvField("With\nNewline")).toBe('"With\nNewline"');
    expect(escapeCsvField(42)).toBe("42");
    expect(escapeCsvField(null)).toBe("");
    expect(escapeCsvField(undefined)).toBe("");
  });

  it("produces correct CSV header with \\r\\n", () => {
    const csv = entriesToCsv([]);
    expect(csv).toBe("Day,Start,End,Duration (slots),Course,Teacher,Division,Room,Session ID");
  });

  it("formats timetable entries with CRLF line breaks and handles commas and quotes", () => {
    const entries: Entry[] = [
      {
        session_id: "FAI|A|1",
        course_id: "FAI",
        course_name: 'Intro to "AI", Basics',
        teacher_id: "T1",
        teacher_name: "Dr. Smith, Jr.",
        division_id: "A",
        division_name: "Div A",
        room_id: "R101",
        room_name: "Lecture Hall 1",
        day: 0,
        day_name: "Mon",
        start_slot: 0,
        end_slot: 1,
        start_time: "09:00",
        end_time: "10:00",
        duration_slots: 1,
      },
      {
        session_id: "MATH|A|1",
        course_id: "MATH",
        course_name: "Calculus",
        teacher_id: "T2",
        teacher_name: "Prof. Müller",
        division_id: "A",
        division_name: "Div A",
        room_id: "R102",
        room_name: "Room 102",
        day: 1,
        day_name: "Tue",
        start_slot: 1,
        end_slot: 3,
        start_time: "10:00",
        end_time: "12:00",
        duration_slots: 2,
      },
    ];

    const csv = entriesToCsv(entries);
    const lines = csv.split("\r\n");
    expect(lines.length).toBe(3);
    expect(lines[0]).toBe("Day,Start,End,Duration (slots),Course,Teacher,Division,Room,Session ID");
    expect(lines[1]).toBe(
      'Mon,09:00,10:00,1,"Intro to ""AI"", Basics","Dr. Smith, Jr.",Div A,Lecture Hall 1,FAI|A|1'
    );
    expect(lines[2]).toBe(
      "Tue,10:00,12:00,2,Calculus,Prof. Müller,Div A,Room 102,MATH|A|1"
    );
  });
});
