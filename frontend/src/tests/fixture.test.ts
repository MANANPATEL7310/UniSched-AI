import { describe, it, expect } from "vitest";
import tinyOutcome from "./fixtures/tiny_outcome.json";

describe("Frontend fixture tiny_outcome.json", () => {
  it("contains valid timetable entries and solved status", () => {
    expect(tinyOutcome.status).toBe("SOLVED");
    expect(tinyOutcome.is_valid).toBe(true);
    expect(tinyOutcome.num_sessions).toBe(5);
    expect(tinyOutcome.timetable).not.toBeNull();
    expect(tinyOutcome.timetable?.entries.length).toBe(5);
  });
});
