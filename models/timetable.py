"""Timetable model and export formats."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any, Mapping

from models.assignment import Assignment
from models.instance import SchedulingInstance


@dataclass(frozen=True)
class Entry:
    """A single scheduled session entry ready for display and tabular export."""

    session_id: str
    course_id: str
    course_name: str
    teacher_id: str
    teacher_name: str
    division_id: str
    division_name: str
    room_id: str
    room_name: str
    day: int
    day_name: str
    start_slot: int
    end_slot: int  # end_slot = start_slot + duration - 1
    start_time: str
    end_time: str
    duration_slots: int


class Timetable:
    """A complete timetable solution mapping sessions to assignments."""

    def __init__(
        self,
        instance: SchedulingInstance,
        assignment: Mapping[str, Assignment],
    ) -> None:
        self.instance = instance
        self.assignment = dict(assignment)

    def entries(self) -> list[Entry]:
        """Return all scheduled entries sorted by (day, start_slot, room_id, session_id)."""
        session_map = {s.session_id: s for s in self.instance.sessions}
        grid = self.instance.grid
        entry_list: list[Entry] = []

        for sid, asgn in self.assignment.items():
            if sid not in session_map:
                continue
            sess = session_map[sid]
            course = self.instance.courses.get(sess.course_id)
            teacher = self.instance.teachers.get(sess.teacher_id)
            division = self.instance.divisions.get(sess.division_id)
            room = self.instance.rooms.get(asgn.room_id)

            day_name = grid.day_names[asgn.day] if 0 <= asgn.day < grid.num_days else f"Day {asgn.day}"
            start_time = (
                grid.slot_starts[asgn.start_slot]
                if 0 <= asgn.start_slot < grid.slots_per_day
                else f"Slot {asgn.start_slot}"
            )
            end_slot = asgn.start_slot + sess.duration_slots - 1
            end_time = (
                grid.slot_ends[end_slot]
                if 0 <= end_slot < grid.slots_per_day
                else f"Slot {end_slot}"
            )

            entry_list.append(
                Entry(
                    session_id=sid,
                    course_id=sess.course_id,
                    course_name=course.name if course else sess.course_id,
                    teacher_id=sess.teacher_id,
                    teacher_name=teacher.name if teacher else sess.teacher_id,
                    division_id=sess.division_id,
                    division_name=division.name if division else sess.division_id,
                    room_id=asgn.room_id,
                    room_name=room.name if room else asgn.room_id,
                    day=asgn.day,
                    day_name=day_name,
                    start_slot=asgn.start_slot,
                    end_slot=end_slot,
                    start_time=start_time,
                    end_time=end_time,
                    duration_slots=sess.duration_slots,
                )
            )

        entry_list.sort(key=lambda e: (e.day, e.start_slot, e.room_id, e.session_id))
        return entry_list

    def view(self, kind: str, key: str | None = None) -> list[Entry]:
        """Filter entries by resource kind: 'division', 'teacher', 'room', 'course', or 'all'."""
        all_entries = self.entries()
        if kind == "all" or key is None:
            return all_entries
        if kind == "division":
            return [e for e in all_entries if e.division_id == key]
        if kind == "teacher":
            return [e for e in all_entries if e.teacher_id == key]
        if kind == "room":
            return [e for e in all_entries if e.room_id == key]
        if kind == "course":
            return [e for e in all_entries if e.course_id == key]
        raise ValueError(f"Unknown view kind '{kind}', expected 'division', 'teacher', 'room', 'course', or 'all'")

    def to_dataframe(self) -> Any:
        """Export entries to a pandas DataFrame (imports pandas lazily)."""
        import pandas as pd  # Lazy import

        columns = [
            "Day",
            "Start",
            "End",
            "Duration (slots)",
            "Course",
            "Teacher",
            "Division",
            "Room",
            "Session ID",
        ]
        data = [
            [
                e.day_name,
                e.start_time,
                e.end_time,
                e.duration_slots,
                e.course_name,
                e.teacher_name,
                e.division_name,
                e.room_name,
                e.session_id,
            ]
            for e in self.entries()
        ]
        return pd.DataFrame(data, columns=columns)

    def to_csv_bytes(self) -> bytes:
        """Export entries to UTF-8 CSV bytes with Excel BOM prefix."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Day",
            "Start",
            "End",
            "Duration (slots)",
            "Course",
            "Teacher",
            "Division",
            "Room",
            "Session ID",
        ])
        for e in self.entries():
            writer.writerow([
                e.day_name,
                e.start_time,
                e.end_time,
                e.duration_slots,
                e.course_name,
                e.teacher_name,
                e.division_name,
                e.room_name,
                e.session_id,
            ])
        # UTF-8 with BOM (\xef\xbb\xbf)
        return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")

    def to_json_dict(self) -> dict:
        """Serialize timetable assignments to JSON dictionary."""
        return {
            "instance_name": self.instance.name,
            "assignments": {
                sid: [asgn.day, asgn.start_slot, asgn.room_id]
                for sid, asgn in self.assignment.items()
            },
        }

    @staticmethod
    def from_json_dict(instance: SchedulingInstance, d: dict) -> Timetable:
        """Build a Timetable object from a serialized JSON dictionary."""
        raw_assignments = d.get("assignments", {})
        assignments: dict[str, Assignment] = {
            sid: Assignment(day=int(v[0]), start_slot=int(v[1]), room_id=str(v[2]))
            for sid, v in raw_assignments.items()
        }
        return Timetable(instance, assignments)
