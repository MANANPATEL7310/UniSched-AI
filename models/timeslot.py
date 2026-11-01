"""TimeGrid representation and slot utilities."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimeGrid:
    """The weekly time grid composed of days and daily time slots."""

    day_names: tuple[str, ...]
    slot_starts: tuple[str, ...]
    slot_ends: tuple[str, ...]

    @property
    def num_days(self) -> int:
        """Total number of days in the grid."""
        return len(self.day_names)

    @property
    def slots_per_day(self) -> int:
        """Number of time slots per day."""
        return len(self.slot_starts)

    def abs_slot(self, day: int, slot: int) -> int:
        """Convert a (day, slot) coordinate to a linear absolute slot index."""
        return day * self.slots_per_day + slot

    def label(self, day: int, slot: int) -> str:
        """Return human-readable label, e.g. 'Mon 09:00'."""
        if not (0 <= day < self.num_days):
            raise ValueError(f"Day index {day} out of range (0..{self.num_days - 1})")
        if not (0 <= slot < self.slots_per_day):
            raise ValueError(f"Slot index {slot} out of range (0..{self.slots_per_day - 1})")
        return f"{self.day_names[day]} {self.slot_starts[slot]}"

    def parse(self, text: str) -> tuple[int, int]:
        """Parse slot string like 'Mon@09:00' into (day_index, slot_index)."""
        if "@" not in text:
            raise ValueError(f"Invalid slot string format '{text}', expected 'DayName@HH:MM'")
        day_str, time_str = text.split("@", 1)
        day_str = day_str.strip()
        time_str = time_str.strip()
        try:
            day_idx = self.day_names.index(day_str)
        except ValueError:
            raise ValueError(f"Unknown day '{day_str}' in slot string '{text}'")
        try:
            slot_idx = self.slot_starts.index(time_str)
        except ValueError:
            raise ValueError(f"Unknown slot start '{time_str}' in slot string '{text}'")
        return day_idx, slot_idx
