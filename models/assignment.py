"""Assignment representation."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Assignment:
    """A placement of a session at a specific day, start slot, and room."""

    day: int
    start_slot: int
    room_id: str
