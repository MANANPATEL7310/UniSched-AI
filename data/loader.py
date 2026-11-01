"""Draft JSON and CSV loaders and converters for SchedulingInstance."""
from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from errors import DataLoadError
from models.assignment import Assignment
from models.course import Course
from models.division import Division
from models.instance import SchedulingInstance, expand_sessions
from models.room import Room
from models.session import ClassSession
from models.teacher import Teacher
from models.timeslot import TimeGrid
from data.schemas import (
    REQUIRED_CSV_FILES,
    CSV_FILE_COLUMNS,
    split_list_cell,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SampleInfo:
    """Metadata describing a bundled sample dataset."""

    name: str
    description: str


def list_samples(base_dir: str | Path = "data/sample_data") -> list[SampleInfo]:
    """List all available sample datasets under data/sample_data/.
    
    Never raises for a malformed sample folder: skips it and logs a warning.
    """
    samples_path = Path(base_dir)
    if not samples_path.exists() or not samples_path.is_dir():
        return []

    samples: list[SampleInfo] = []
    for item in sorted(samples_path.iterdir()):
        if not item.is_dir():
            continue
        info_file = item / "info.json"
        description = "No description available."
        if info_file.exists():
            try:
                data = json.loads(info_file.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "description" in data:
                    description = str(data["description"])
                else:
                    logger.warning("Sample %s info.json missing 'description' key", item.name)
            except Exception as e:
                logger.warning("Failed to parse info.json in %s: %s", item.name, e)
                continue
        samples.append(SampleInfo(name=item.name, description=description))
    return samples


def load_sample(name: str, base_dir: str | Path = "data/sample_data") -> dict:
    """Load a named sample folder from data/sample_data/<name> as a draft dictionary.
    
    Raises:
        DataLoadError: if the sample is unknown or files are missing/malformed.
    """
    sample_dir = Path(base_dir) / name
    if not sample_dir.exists() or not sample_dir.is_dir():
        raise DataLoadError(f"Unknown sample '{name}'")

    csv_files: dict[str, bytes] = {}
    for file_path in sample_dir.glob("*.csv"):
        csv_files[file_path.name] = file_path.read_bytes()

    draft = draft_from_csv_files(csv_files)
    draft["name"] = name
    return draft


def _read_csv_rows(
    filename: str,
    content: bytes,
    required_columns: tuple[str, ...],
    allow_empty: bool = False,
) -> list[dict[str, str]]:
    """Decode and parse CSV content using utf-8-sig, validating headers and line numbers."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise DataLoadError(f"{filename}: invalid UTF-8 encoding ({e})") from e

    lines = text.splitlines()
    non_empty_lines = [l for l in lines if l.strip()]
    if not non_empty_lines:
        if allow_empty:
            return []
        raise DataLoadError(f"{filename} has no rows")

    reader = csv.DictReader(lines)
    if reader.fieldnames is None:
        if allow_empty:
            return []
        raise DataLoadError(f"{filename} has no rows")

    cleaned_fieldnames = [f.strip() if f else "" for f in reader.fieldnames]
    reader.fieldnames = cleaned_fieldnames

    for col in required_columns:
        if col not in cleaned_fieldnames:
            raise DataLoadError(f"{filename}: missing column '{col}'")

    extra_cols = set(cleaned_fieldnames) - set(required_columns)
    if extra_cols:
        logger.warning(f"{filename}: ignoring extra columns {extra_cols}")

    rows: list[dict[str, str]] = []
    for row in reader:
        cleaned_row = {
            k.strip(): (v.strip() if v else "")
            for k, v in row.items()
            if k is not None
        }
        if not any(cleaned_row.values()):
            continue
        cleaned_row["__line_num__"] = str(reader.line_num)
        rows.append(cleaned_row)

    if not rows and not allow_empty:
        raise DataLoadError(f"{filename} has no rows")

    return rows


def draft_from_csv_files(files: dict[str, bytes]) -> dict:
    """Parse raw CSV file contents into an editable draft JSON dictionary.
    
    Raises:
        DataLoadError: if required files/columns are missing or numbers are invalid.
    """
    normalized_files = {k.lower(): v for k, v in files.items()}

    for req in REQUIRED_CSV_FILES:
        if req not in normalized_files:
            raise DataLoadError(f"Missing file: {req}")

    # 1. days.csv
    days_rows = _read_csv_rows(
        "days.csv", normalized_files["days.csv"], CSV_FILE_COLUMNS["days.csv"]
    )
    days = [r["day_name"] for r in days_rows]

    # 2. slots.csv
    slots_rows = _read_csv_rows(
        "slots.csv", normalized_files["slots.csv"], CSV_FILE_COLUMNS["slots.csv"]
    )
    slots = [{"start": r["start_time"], "end": r["end_time"]} for r in slots_rows]

    # 3. teachers.csv
    teachers_rows = _read_csv_rows(
        "teachers.csv", normalized_files["teachers.csv"], CSV_FILE_COLUMNS["teachers.csv"]
    )
    teachers: list[dict] = []
    for r in teachers_rows:
        max_daily: int | None = None
        raw_max = r.get("max_daily_sessions", "")
        if raw_max:
            try:
                max_daily = int(raw_max)
            except ValueError:
                raise DataLoadError(
                    f"teachers.csv row {r['__line_num__']}: max_daily_sessions '{raw_max}' is not a whole number"
                )
        teachers.append({
            "teacher_id": r["teacher_id"],
            "teacher_name": r.get("teacher_name", ""),
            "unavailable_slots": split_list_cell(r.get("unavailable_slots", "")),
            "preferred_slots": split_list_cell(r.get("preferred_slots", "")),
            "max_daily_sessions": max_daily,
        })

    # 4. courses.csv
    courses_rows = _read_csv_rows(
        "courses.csv", normalized_files["courses.csv"], CSV_FILE_COLUMNS["courses.csv"]
    )
    courses: list[dict] = []
    for r in courses_rows:
        raw_spw = r.get("sessions_per_week", "")
        try:
            spw = int(raw_spw)
        except ValueError:
            raise DataLoadError(
                f"courses.csv row {r['__line_num__']}: sessions_per_week '{raw_spw}' is not a whole number"
            )

        raw_dur = r.get("duration_slots", "")
        try:
            dur = int(raw_dur)
        except ValueError:
            raise DataLoadError(
                f"courses.csv row {r['__line_num__']}: duration_slots '{raw_dur}' is not a whole number"
            )

        courses.append({
            "course_id": r["course_id"],
            "course_name": r.get("course_name", ""),
            "teacher_id": r["teacher_id"],
            "sessions_per_week": spw,
            "duration_slots": dur,
            "room_types": split_list_cell(r.get("room_types", "")),
            "eligible_divisions": split_list_cell(r.get("eligible_divisions", "")),
        })

    # 5. divisions.csv
    divisions_rows = _read_csv_rows(
        "divisions.csv", normalized_files["divisions.csv"], CSV_FILE_COLUMNS["divisions.csv"]
    )
    divisions: list[dict] = []
    for r in divisions_rows:
        raw_count = r.get("student_count", "")
        try:
            count = int(raw_count)
        except ValueError:
            raise DataLoadError(
                f"divisions.csv row {r['__line_num__']}: student_count '{raw_count}' is not a whole number"
            )

        divisions.append({
            "division_id": r["division_id"],
            "division_name": r.get("division_name", ""),
            "student_count": count,
            "enrolled_courses": split_list_cell(r.get("enrolled_courses", "")),
        })

    # 6. rooms.csv
    rooms_rows = _read_csv_rows(
        "rooms.csv", normalized_files["rooms.csv"], CSV_FILE_COLUMNS["rooms.csv"]
    )
    rooms: list[dict] = []
    for r in rooms_rows:
        raw_cap = r.get("capacity", "")
        try:
            cap = int(raw_cap)
        except ValueError:
            raise DataLoadError(
                f"rooms.csv row {r['__line_num__']}: capacity '{raw_cap}' is not a whole number"
            )

        rooms.append({
            "room_id": r["room_id"],
            "room_name": r.get("room_name", ""),
            "room_type": r["room_type"],
            "capacity": cap,
            "unavailable_slots": split_list_cell(r.get("unavailable_slots", "")),
        })

    # 7. fixed_assignments.csv (optional)
    fixed_assignments: list[dict] = []
    if "fixed_assignments.csv" in normalized_files:
        fixed_rows = _read_csv_rows(
            "fixed_assignments.csv",
            normalized_files["fixed_assignments.csv"],
            CSV_FILE_COLUMNS["fixed_assignments.csv"],
            allow_empty=True,
        )
        for r in fixed_rows:
            fixed_assignments.append({
                "session_id": r["session_id"],
                "day_name": r["day_name"],
                "start_time": r["start_time"],
                "room_id": r["room_id"],
            })

    return {
        "name": "uploaded",
        "days": days,
        "slots": slots,
        "teachers": teachers,
        "courses": courses,
        "divisions": divisions,
        "rooms": rooms,
        "fixed_assignments": fixed_assignments,
    }


def instance_from_draft(draft: dict) -> SchedulingInstance:
    """Build a validated SchedulingInstance dataclass tree from a draft dictionary.
    
    Raises:
        DataLoadError: on malformed structure, missing keys, duplicate IDs, or invalid slot strings.
    """
    if not isinstance(draft, dict):
        raise DataLoadError("Draft must be a dictionary object")

    # 1. Structure check
    required_keys = ("days", "slots", "teachers", "courses", "divisions", "rooms")
    for key in required_keys:
        if key not in draft:
            raise DataLoadError(f"Draft is missing '{key}'")
        if not isinstance(draft[key], list):
            raise DataLoadError(f"Draft field '{key}' must be a list")

    fixed_list = draft.get("fixed_assignments", [])
    if fixed_list is not None and not isinstance(fixed_list, list):
        raise DataLoadError("Draft field 'fixed_assignments' must be a list")

    # 2. TimeGrid
    days = draft["days"]
    if not days:
        raise DataLoadError("Draft has no days defined")

    seen_days = set()
    for d in days:
        if not isinstance(d, str) or not d.strip():
            raise DataLoadError(f"Invalid day name '{d}'")
        if d in seen_days:
            raise DataLoadError(f"Duplicate day name '{d}'")
        seen_days.add(d)

    slots_defs = draft["slots"]
    if not slots_defs:
        raise DataLoadError("Draft has no slots defined")

    slot_starts: list[str] = []
    slot_ends: list[str] = []
    seen_starts = set()
    for s_def in slots_defs:
        if not isinstance(s_def, dict) or "start" not in s_def or "end" not in s_def:
            raise DataLoadError("Slot definition must contain 'start' and 'end'")
        s_start = str(s_def["start"]).strip()
        s_end = str(s_def["end"]).strip()
        if s_start in seen_starts:
            raise DataLoadError(f"Duplicate slot start time '{s_start}'")
        seen_starts.add(s_start)
        if s_start >= s_end:
            raise DataLoadError(f"Slot start time '{s_start}' must be earlier than end time '{s_end}'")
        slot_starts.append(s_start)
        slot_ends.append(s_end)

    grid = TimeGrid(
        day_names=tuple(days),
        slot_starts=tuple(slot_starts),
        slot_ends=tuple(slot_ends),
    )

    # Helper for parsing slot strings
    def _parse_slot_set(entity_name: str, slot_list: list[str]) -> frozenset[tuple[int, int]]:
        coords: set[tuple[int, int]] = set()
        for slot_str in slot_list:
            if not isinstance(slot_str, str):
                raise DataLoadError(f"{entity_name}: slot identifier must be a string, got '{slot_str}'")
            try:
                coords.add(grid.parse(slot_str))
            except ValueError:
                raise DataLoadError(f"{entity_name}: '{slot_str}' is not a slot of the grid")
        return frozenset(coords)

    # 3 & 4. Teachers
    teachers_dict: dict[str, Teacher] = {}
    for t in draft["teachers"]:
        if not isinstance(t, dict):
            raise DataLoadError("Teacher entry must be a dictionary")
        t_id = t.get("teacher_id")
        if not t_id or not isinstance(t_id, str):
            raise DataLoadError("Teacher entry missing 'teacher_id'")
        if t_id in teachers_dict:
            raise DataLoadError(f"duplicate teacher_id '{t_id}'")

        unav = _parse_slot_set(f"teachers[{t_id}].unavailable_slots", t.get("unavailable_slots", []))
        pref = _parse_slot_set(f"teachers[{t_id}].preferred_slots", t.get("preferred_slots", []))
        teachers_dict[t_id] = Teacher(
            teacher_id=t_id,
            name=t.get("teacher_name", t_id) or t_id,
            unavailable=unav,
            preferred=pref,
            max_daily_sessions=t.get("max_daily_sessions"),
        )

    # Rooms
    rooms_dict: dict[str, Room] = {}
    for r in draft["rooms"]:
        if not isinstance(r, dict):
            raise DataLoadError("Room entry must be a dictionary")
        r_id = r.get("room_id")
        if not r_id or not isinstance(r_id, str):
            raise DataLoadError("Room entry missing 'room_id'")
        if r_id in rooms_dict:
            raise DataLoadError(f"duplicate room_id '{r_id}'")

        unav = _parse_slot_set(f"rooms[{r_id}].unavailable_slots", r.get("unavailable_slots", []))
        rooms_dict[r_id] = Room(
            room_id=r_id,
            name=r.get("room_name", r_id) or r_id,
            room_type=r.get("room_type", ""),
            capacity=r.get("capacity", 0),
            unavailable=unav,
        )

    # Courses
    courses_dict: dict[str, Course] = {}
    for c in draft["courses"]:
        if not isinstance(c, dict):
            raise DataLoadError("Course entry must be a dictionary")
        c_id = c.get("course_id")
        if not c_id or not isinstance(c_id, str):
            raise DataLoadError("Course entry missing 'course_id'")
        if c_id in courses_dict:
            raise DataLoadError(f"duplicate course_id '{c_id}'")

        courses_dict[c_id] = Course(
            course_id=c_id,
            name=c.get("course_name", c_id) or c_id,
            teacher_id=c.get("teacher_id", ""),
            sessions_per_week=c.get("sessions_per_week", 0),
            duration_slots=c.get("duration_slots", 1),
            room_types=tuple(c.get("room_types", [])),
            eligible_divisions=tuple(c.get("eligible_divisions", [])),
        )

    # Divisions
    divisions_dict: dict[str, Division] = {}
    for d in draft["divisions"]:
        if not isinstance(d, dict):
            raise DataLoadError("Division entry must be a dictionary")
        d_id = d.get("division_id")
        if not d_id or not isinstance(d_id, str):
            raise DataLoadError("Division entry missing 'division_id'")
        if d_id in divisions_dict:
            raise DataLoadError(f"duplicate division_id '{d_id}'")

        divisions_dict[d_id] = Division(
            division_id=d_id,
            name=d.get("division_name", d_id) or d_id,
            student_count=d.get("student_count", 0),
            enrolled_courses=tuple(d.get("enrolled_courses", [])),
        )

    # 6. Fixed assignments
    fixed_map: dict[str, Assignment] = {}
    if fixed_list:
        for f in fixed_list:
            if not isinstance(f, dict):
                raise DataLoadError("Fixed assignment entry must be a dictionary")
            sid = f.get("session_id")
            if not sid:
                raise DataLoadError("Fixed assignment missing 'session_id'")
            if sid in fixed_map:
                raise DataLoadError(f"Duplicate fixed assignment for session '{sid}'")

            day_name = f.get("day_name", "")
            if day_name not in grid.day_names:
                raise DataLoadError(f"fixed_assignments: unknown day_name '{day_name}'")

            start_time = f.get("start_time", "")
            if start_time not in grid.slot_starts:
                raise DataLoadError(f"fixed_assignments: unknown start_time '{start_time}'")

            room_id = f.get("room_id", "")
            day_idx = grid.day_names.index(day_name)
            slot_idx = grid.slot_starts.index(start_time)
            fixed_map[sid] = Assignment(day=day_idx, start_slot=slot_idx, room_id=room_id)

    # 7. Expand sessions
    sessions = expand_sessions(courses=courses_dict, divisions=divisions_dict, fixed=fixed_map)

    return SchedulingInstance(
        name=draft.get("name", "Untitled"),
        grid=grid,
        teachers=teachers_dict,
        rooms=rooms_dict,
        divisions=divisions_dict,
        courses=courses_dict,
        sessions=sessions,
        meta={"source": draft.get("name"), "fixed_session_ids": tuple(fixed_map.keys())},
    )


def draft_from_instance(inst: SchedulingInstance) -> dict:
    """Export a SchedulingInstance to an editable draft dictionary."""
    teachers_list: list[dict] = []
    for t in inst.teachers.values():
        unav = [
            f"{inst.grid.day_names[d]}@{inst.grid.slot_starts[s]}"
            for d, s in sorted(t.unavailable)
        ]
        pref = [
            f"{inst.grid.day_names[d]}@{inst.grid.slot_starts[s]}"
            for d, s in sorted(t.preferred)
        ]
        teachers_list.append({
            "teacher_id": t.teacher_id,
            "teacher_name": t.name,
            "unavailable_slots": unav,
            "preferred_slots": pref,
            "max_daily_sessions": t.max_daily_sessions,
        })

    courses_list: list[dict] = []
    for c in inst.courses.values():
        courses_list.append({
            "course_id": c.course_id,
            "course_name": c.name,
            "teacher_id": c.teacher_id,
            "sessions_per_week": c.sessions_per_week,
            "duration_slots": c.duration_slots,
            "room_types": list(c.room_types),
            "eligible_divisions": list(c.eligible_divisions),
        })

    divisions_list: list[dict] = []
    for d in inst.divisions.values():
        divisions_list.append({
            "division_id": d.division_id,
            "division_name": d.name,
            "student_count": d.student_count,
            "enrolled_courses": list(d.enrolled_courses),
        })

    rooms_list: list[dict] = []
    for r in inst.rooms.values():
        unav = [
            f"{inst.grid.day_names[d]}@{inst.grid.slot_starts[s]}"
            for d, s in sorted(r.unavailable)
        ]
        rooms_list.append({
            "room_id": r.room_id,
            "room_name": r.name,
            "room_type": r.room_type,
            "capacity": r.capacity,
            "unavailable_slots": unav,
        })

    fixed_list: list[dict] = []
    for s in inst.sessions:
        if s.fixed is not None:
            fixed_list.append({
                "session_id": s.session_id,
                "day_name": inst.grid.day_names[s.fixed.day],
                "start_time": inst.grid.slot_starts[s.fixed.start_slot],
                "room_id": s.fixed.room_id,
            })
    fixed_list.sort(key=lambda x: x["session_id"])

    return {
        "name": inst.name,
        "days": list(inst.grid.day_names),
        "slots": [
            {"start": s, "end": e}
            for s, e in zip(inst.grid.slot_starts, inst.grid.slot_ends)
        ],
        "teachers": teachers_list,
        "courses": courses_list,
        "divisions": divisions_list,
        "rooms": rooms_list,
        "fixed_assignments": fixed_list,
    }
