import type { Entry } from "../api/types";

export interface Block {
  entry: Entry;
  col: number;
  rowStart: number;
  rowSpan: number;
}

export interface StackedCell {
  col: number;
  row: number;
  items: { entry: Entry; cont: boolean }[];
}

export type WeekGridModel =
  | { mode: "blocks"; rows: number; cols: number; days: number[]; blocks: Block[] }
  | { mode: "stacked"; rows: number; cols: number; days: number[]; cells: StackedCell[] };

export function buildWeekGrid(
  entries: Entry[],
  slotsPerDay: number,
  days: number[]
): WeekGridModel {
  // 1. Filter entries to visible days
  const visible = entries.filter((e) => days.includes(e.day));

  // 2. Build occupancy counts per (day, slot)
  const occupancy = new Map<string, number>();
  for (const e of visible) {
    const dur = e.duration_slots || (e.end_slot - e.start_slot) || 1;
    for (let slot = e.start_slot; slot < e.start_slot + dur; slot++) {
      const key = `${e.day}@${slot}`;
      occupancy.set(key, (occupancy.get(key) || 0) + 1);
    }
  }

  // 3. Check if any slot has overlapping entries (> 1)
  const hasOverlap = Array.from(occupancy.values()).some((count) => count > 1);

  if (hasOverlap) {
    // STACKED mode
    const cells: StackedCell[] = [];
    for (let col = 0; col < days.length; col++) {
      const day = days[col]!;
      for (let row = 0; row < slotsPerDay; row++) {
        const covering = visible.filter((e) => {
          const dur = e.duration_slots || (e.end_slot - e.start_slot) || 1;
          return e.day === day && row >= e.start_slot && row < e.start_slot + dur;
        });

        if (covering.length > 0) {
          cells.push({
            col,
            row,
            items: covering.map((entry) => ({
              entry,
              cont: row > entry.start_slot,
            })),
          });
        }
      }
    }

    return {
      mode: "stacked",
      rows: slotsPerDay,
      cols: days.length,
      days,
      cells,
    };
  }

  // 4. BLOCKS mode (conflict-free / non-overlapping)
  const blocks: Block[] = visible.map((e) => {
    const col = days.indexOf(e.day);
    const rowStart = e.start_slot;
    const rowSpan = e.duration_slots || (e.end_slot - e.start_slot) || 1;
    return { entry: e, col, rowStart, rowSpan };
  });

  return {
    mode: "blocks",
    rows: slotsPerDay,
    cols: days.length,
    days,
    blocks,
  };
}

