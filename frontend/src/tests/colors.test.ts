import { describe, expect, it } from "vitest";
import { courseColor } from "../lib/colors.js";

describe("colors library", () => {
  it("assigns consistent colors to same course regardless of input order", () => {
    const list1 = ["MATH", "PHYS", "CHEM"];
    const list2 = ["CHEM", "MATH", "PHYS"];

    const cMath1 = courseColor("MATH", list1);
    const cMath2 = courseColor("MATH", list2);

    expect(cMath1.hue).toBe(cMath2.hue);
    expect(cMath1.backgroundColor).toBe(cMath2.backgroundColor);
  });

  it("assigns distinct hues to different courses", () => {
    const list = ["C1", "C2", "C3", "C4"];
    const hues = list.map((c) => courseColor(c, list).hue);
    const uniqueHues = new Set(hues);
    expect(uniqueHues.size).toBe(list.length);
  });

  it("handles unknown or empty list gracefully", () => {
    const col = courseColor("NEW", []);
    expect(typeof col.hue).toBe("number");
    expect(col.backgroundColor).toContain("hsl(");
  });
});
