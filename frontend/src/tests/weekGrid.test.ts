import { describe, expect, it } from "vitest";
import { buildWeekGrid } from "../lib/weekGrid";
import type { Entry } from "../api/types";

function createMockEntry(overrides: Partial<Entry>): Entry {
  return {
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
    ...overrides,
  };
}

describe("weekGrid library", () => {
  it("handles empty entries list in blocks mode", () => {
    const grid = buildWeekGrid([], 6, [0, 1, 2, 3, 4]);
    expect(grid.mode).toBe("blocks");
    if (grid.mode === "blocks") {
      expect(grid.blocks).toEqual([]);
      expect(grid.rows).toBe(6);
      expect(grid.cols).toBe(5);
    }
  });

  it("places single 1-slot entry as a block with rowSpan 1", () => {
    const e = createMockEntry({ day: 1, start_slot: 2, end_slot: 3, duration_slots: 1 });
    const grid = buildWeekGrid([e], 6, [0, 1, 2]);

    expect(grid.mode).toBe("blocks");
    if (grid.mode === "blocks") {
      expect(grid.blocks.length).toBe(1);
      expect(grid.blocks[0]?.col).toBe(1); // day 1 is at index 1 of [0, 1, 2]
      expect(grid.blocks[0]?.rowStart).toBe(2);
      expect(grid.blocks[0]?.rowSpan).toBe(1);
    }
  });

  it("renders 2-slot lab as one block with rowSpan 2", () => {
    const lab = createMockEntry({
      session_id: "PLAB|A|1",
      course_id: "PLAB",
      day: 0,
      start_slot: 1,
      end_slot: 3,
      duration_slots: 2,
    });
    const grid = buildWeekGrid([lab], 6, [0, 1, 2]);

    expect(grid.mode).toBe("blocks");
    if (grid.mode === "blocks") {
      expect(grid.blocks.length).toBe(1);
      expect(grid.blocks[0]?.rowStart).toBe(1);
      expect(grid.blocks[0]?.rowSpan).toBe(2);
    }
  });

  it("switches to stacked mode when two entries overlap in time and day", () => {
    const e1 = createMockEntry({
      session_id: "C1|A|1",
      day: 0,
      start_slot: 1,
      end_slot: 3,
      duration_slots: 2,
    });
    const e2 = createMockEntry({
      session_id: "C2|A|1",
      day: 0,
      start_slot: 2,
      end_slot: 3,
      duration_slots: 1,
    });

    const grid = buildWeekGrid([e1, e2], 6, [0, 1]);
    expect(grid.mode).toBe("stacked");

    if (grid.mode === "stacked") {
      // Slot 1 has e1 (cont = false)
      const slot1 = grid.cells.find((c) => c.col === 0 && c.row === 1);
      expect(slot1).toBeDefined();
      expect(slot1?.items.length).toBe(1);
      expect(slot1?.items[0]?.entry.session_id).toBe("C1|A|1");
      expect(slot1?.items[0]?.cont).toBe(false);

      // Slot 2 has both e1 (cont = true) and e2 (cont = false)
      const slot2 = grid.cells.find((c) => c.col === 0 && c.row === 2);
      expect(slot2).toBeDefined();
      expect(slot2?.items.length).toBe(2);
      const e1InSlot2 = slot2?.items.find((i) => i.entry.session_id === "C1|A|1");
      const e2InSlot2 = slot2?.items.find((i) => i.entry.session_id === "C2|A|1");
      expect(e1InSlot2?.cont).toBe(true);
      expect(e2InSlot2?.cont).toBe(false);
    }
  });

  it("filters out entries for days not in the days list", () => {
    const eMon = createMockEntry({ day: 0 });
    const eFri = createMockEntry({ day: 4 });

    const grid = buildWeekGrid([eMon, eFri], 6, [0, 1, 2]); // only Mon, Tue, Wed
    expect(grid.mode).toBe("blocks");
    if (grid.mode === "blocks") {
      expect(grid.blocks.length).toBe(1);
      expect(grid.blocks[0]?.entry.day).toBe(0);
    }
  });
});
