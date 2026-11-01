import { describe, expect, it } from "vitest";
import {
  compareTimes,
  formatTimeRange,
  parseSlotKey,
  slotKey,
} from "../lib/slots.js";

describe("slots library", () => {
  it("creates slot key correctly", () => {
    expect(slotKey("Mon", "09:00")).toBe("Mon@09:00");
    expect(slotKey("Fri", "16:00")).toBe("Fri@16:00");
  });

  it("parses valid slot keys", () => {
    expect(parseSlotKey("Mon@09:00")).toEqual({ day: "Mon", startTime: "09:00" });
    expect(parseSlotKey("Wed @ 14:00 ")).toEqual({ day: "Wed", startTime: "14:00" });
  });

  it("returns null for malformed slot keys", () => {
    expect(parseSlotKey("")).toBeNull();
    expect(parseSlotKey("Mon")).toBeNull();
    expect(parseSlotKey("Mon@09:00@Extra")).toBeNull();
    expect(parseSlotKey("@09:00")).toBeNull();
    expect(parseSlotKey("Mon@")).toBeNull();
  });

  it("formats time ranges", () => {
    expect(formatTimeRange("09:00", "10:00")).toBe("09:00–10:00");
  });

  it("compares times lexicographically", () => {
    expect(compareTimes("09:00", "10:00")).toBeLessThan(0);
    expect(compareTimes("10:00", "09:00")).toBeGreaterThan(0);
    expect(compareTimes("09:00", "09:00")).toBe(0);
  });
});
