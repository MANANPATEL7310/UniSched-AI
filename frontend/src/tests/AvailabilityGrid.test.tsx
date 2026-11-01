import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AvailabilityGrid } from "../components/AvailabilityGrid";

describe("AvailabilityGrid", () => {
  const days = ["Mon", "Tue"];
  const slots = [
    { start: "09:00", end: "10:00" },
    { start: "10:00", end: "11:00" },
  ];

  it("renders checkboxes for all days and slots", () => {
    render(
      <AvailabilityGrid
        days={days}
        slots={slots}
        value={["Mon@09:00"]}
        onChange={vi.fn()}
        label="Test Availability"
      />
    );

    expect(screen.getByText("Test Availability")).toBeInTheDocument();
    expect(screen.getByText("1 slot(s) selected")).toBeInTheDocument();

    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes.length).toBe(4); // 2 days * 2 slots
    expect(checkboxes[0]).toBeChecked(); // Mon@09:00
    expect(checkboxes[1]).not.toBeChecked();
  });

  it("calls onChange when toggling a checkbox", () => {
    const handleChange = vi.fn();
    render(
      <AvailabilityGrid
        days={days}
        slots={slots}
        value={["Mon@09:00"]}
        onChange={handleChange}
        label="Test Availability"
      />
    );

    const checkboxes = screen.getAllByRole("checkbox");
    // Toggle Mon@09:00 off
    fireEvent.click(checkboxes[0]!);
    expect(handleChange).toHaveBeenCalledWith([]);

    // Toggle Tue@09:00 on
    fireEvent.click(checkboxes[1]!);
    expect(handleChange).toHaveBeenCalledWith(["Mon@09:00", "Tue@09:00"]);
  });

  it("selects all slots on Select All button click", () => {
    const handleChange = vi.fn();
    render(
      <AvailabilityGrid
        days={days}
        slots={slots}
        value={[]}
        onChange={handleChange}
        label="Test Availability"
      />
    );

    fireEvent.click(screen.getByText("Select All"));
    expect(handleChange).toHaveBeenCalledWith([
      "Mon@09:00",
      "Mon@10:00",
      "Tue@09:00",
      "Tue@10:00",
    ]);
  });

  it("preserves unknown slots when Clear is clicked", () => {
    const handleChange = vi.fn();
    render(
      <AvailabilityGrid
        days={days}
        slots={slots}
        value={["Mon@09:00", "Sun@08:00"]} // Sun@08:00 is unknown
        onChange={handleChange}
        label="Test Availability"
      />
    );

    expect(screen.getByText(/Unknown slots retained:/i)).toBeInTheDocument();
    expect(screen.getByText(/Sun@08:00/i)).toBeInTheDocument();

    fireEvent.click(screen.getByText("Clear"));
    expect(handleChange).toHaveBeenCalledWith(["Sun@08:00"]);
  });
});
