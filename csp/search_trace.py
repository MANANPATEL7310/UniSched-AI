"""Search trace recording data structures for visualising and debugging CSP search."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TraceEventKind(str, Enum):
    """Categorisation of CSP search tree events."""

    SELECT_VAR = "SELECT_VAR"
    TRY_VALUE = "TRY_VALUE"
    ASSIGN = "ASSIGN"
    PRUNE = "PRUNE"
    WIPEOUT = "WIPEOUT"
    BACKTRACK = "BACKTRACK"


@dataclass(frozen=True)
class TraceEvent:
    """A single discrete step or decision in the CSP search tree."""

    kind: str
    session_id: str
    value_label: str
    note: str = ""
    depth: int = 0

