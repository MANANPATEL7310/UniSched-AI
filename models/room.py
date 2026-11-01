"""Room representation."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Room:
    """Physical room/laboratory with type, seating capacity, and availability."""

    room_id: str
    name: str
    room_type: str
    capacity: int
    unavailable: frozenset[tuple[int, int]] = frozenset()
