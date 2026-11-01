"""Unit tests for data schemas and loader (CSV <-> draft <-> instance)."""
from __future__ import annotations

import copy
import pytest

from errors import DataLoadError
from data.schemas import (
    ROOM_TYPES,
    REQUIRED_CSV_FILES,
    split_list_cell,
    join_list_cell,
    format_slot,
    parse_slot_string,
)
from data.loader import (
    SampleInfo,
    list_samples,
    load_sample,
    draft_from_csv_files,
    instance_from_draft,
    draft_from_instance,
)


# --- Schemas tests ---

def test_schemas_utilities():
    assert ROOM_TYPES == ("lecture", "computer_lab", "general_lab")
    assert "courses.csv" in REQUIRED_CSV_FILES

    assert split_list_cell("A; B ; ; C") == ["A", "B", "C"]
    assert split_list_cell("") == []
    assert split_list_cell(None) == []

    assert join_list_cell(["A", "B", "C"]) == "A;B;C"

    assert format_slot("Mon", "09:00") == "Mon@09:00"
    assert parse_slot_string("Mon@09:00") == ("Mon", "09:00")

    with pytest.raises(DataLoadError, match="Invalid slot string format"):
        parse_slot_string("Mon09:00")
    with pytest.raises(DataLoadError, match="Invalid slot string format"):
        parse_slot_string("@09:00")


# --- Sample loading tests ---

def test_list_samples():
    samples = list_samples()
    assert isinstance(samples, list)
    assert len(samples) >= 1
    tiny_sample = next((s for s in samples if s.name == "tiny"), None)
    assert tiny_sample is not None
    assert "Tiny" in tiny_sample.description


def test_load_sample_tiny():
    draft = load_sample("tiny")
    assert draft["name"] == "tiny"
    assert "days" in draft
    assert "slots" in draft
    assert "teachers" in draft
    assert "courses" in draft
    assert "divisions" in draft
    assert "rooms" in draft
    assert "fixed_assignments" in draft
    assert len(draft["days"]) == 2
    assert len(draft["slots"]) == 3


def test_load_sample_unknown():
    with pytest.raises(DataLoadError, match="Unknown sample 'nonexistent_sample'"):
        load_sample("nonexistent_sample")


# --- Instance from draft & Round trip tests ---

def test_instance_from_tiny_draft_and_roundtrip():
    draft = load_sample("tiny")
    instance = instance_from_draft(draft)

    assert instance.name == "tiny"
    assert instance.grid.num_days == 2
    assert instance.grid.slots_per_day == 3
    assert len(instance.teachers) == 3
    assert len(instance.rooms) == 3
    assert len(instance.courses) == 3
    assert len(instance.divisions) == 2
    # 2 for FAI|A, 1 for MATH|A, 1 for MATH|B, 1 for PLAB|A = 5 sessions
    assert len(instance.sessions) == 5

    fixed_sess = next(s for s in instance.sessions if s.session_id == "FAI|A|1")
    assert fixed_sess.fixed is not None
    assert fixed_sess.fixed.day == 0  # Mon
    assert fixed_sess.fixed.start_slot == 1  # 10:00 is slot 1
    assert fixed_sess.fixed.room_id == "R101"

    # Round trip: draft -> instance -> draft -> instance
    exported_draft = draft_from_instance(instance)
    rebuilt_instance = instance_from_draft(exported_draft)

    assert rebuilt_instance.name == instance.name
    assert rebuilt_instance.grid == instance.grid
    assert rebuilt_instance.teachers == instance.teachers
    assert rebuilt_instance.rooms == instance.rooms
    assert rebuilt_instance.courses == instance.courses
    assert rebuilt_instance.divisions == instance.divisions
    assert rebuilt_instance.sessions == instance.sessions


# --- CSV parsing and error handling tests ---

def _get_valid_csv_files() -> dict[str, bytes]:
    return {
        "days.csv": b"day_name\nMon\nTue\n",
        "slots.csv": b"start_time,end_time\n09:00,10:00\n10:00,11:00\n",
        "teachers.csv": b"teacher_id,teacher_name,unavailable_slots,preferred_slots,max_daily_sessions\nT01,Dr. Rao,Mon@09:00,,3\n",
        "courses.csv": b"course_id,course_name,teacher_id,sessions_per_week,duration_slots,room_types,eligible_divisions\nFAI,AI,T01,1,1,lecture,A\n",
        "divisions.csv": b"division_id,division_name,student_count,enrolled_courses\nA,Div A,50,FAI\n",
        "rooms.csv": b"room_id,room_name,room_type,capacity,unavailable_slots\nR101,Room 101,lecture,60,\n",
        "fixed_assignments.csv": b"session_id,day_name,start_time,room_id\nFAI|A|1,Mon,10:00,R101\n",
    }


def test_draft_from_csv_files_valid():
    files = _get_valid_csv_files()
    draft = draft_from_csv_files(files)
    assert draft["days"] == ["Mon", "Tue"]
    assert len(draft["teachers"]) == 1
    assert draft["teachers"][0]["max_daily_sessions"] == 3
    assert draft["teachers"][0]["unavailable_slots"] == ["Mon@09:00"]
    assert len(draft["fixed_assignments"]) == 1


def test_draft_from_csv_files_with_bom():
    files = _get_valid_csv_files()
    # Add UTF-8 BOM to days.csv
    files["days.csv"] = b"\xef\xbb\xbfday_name\nMon\nTue\n"
    draft = draft_from_csv_files(files)
    assert draft["days"] == ["Mon", "Tue"]


def test_draft_from_csv_files_extra_columns():
    files = _get_valid_csv_files()
    files["rooms.csv"] = b"room_id,room_name,room_type,capacity,unavailable_slots,extra_notes\nR101,Room 101,lecture,60,,Nice room\n"
    draft = draft_from_csv_files(files)
    assert draft["rooms"][0]["room_id"] == "R101"


def test_draft_missing_required_file():
    files = _get_valid_csv_files()
    del files["courses.csv"]
    with pytest.raises(DataLoadError, match="Missing file: courses.csv"):
        draft_from_csv_files(files)


def test_draft_missing_required_column():
    files = _get_valid_csv_files()
    files["courses.csv"] = b"course_id,course_name,sessions_per_week,duration_slots,room_types,eligible_divisions\nFAI,AI,1,1,lecture,A\n"
    with pytest.raises(DataLoadError, match="courses.csv: missing column 'teacher_id'"):
        draft_from_csv_files(files)


def test_draft_text_in_number_column():
    files = _get_valid_csv_files()
    # Header is row 1, data row is row 2
    files["rooms.csv"] = b"room_id,room_name,room_type,capacity,unavailable_slots\nR101,Room 101,lecture,abc,\n"
    with pytest.raises(DataLoadError, match="rooms.csv row 2: capacity 'abc' is not a whole number"):
        draft_from_csv_files(files)

    files = _get_valid_csv_files()
    files["courses.csv"] = b"course_id,course_name,teacher_id,sessions_per_week,duration_slots,room_types,eligible_divisions\nFAI,AI,T01,xyz,1,lecture,A\n"
    with pytest.raises(DataLoadError, match="courses.csv row 2: sessions_per_week 'xyz' is not a whole number"):
        draft_from_csv_files(files)


def test_draft_empty_file():
    files = _get_valid_csv_files()
    files["teachers.csv"] = b""
    with pytest.raises(DataLoadError, match="teachers.csv has no rows"):
        draft_from_csv_files(files)

    files["teachers.csv"] = b"teacher_id,teacher_name,unavailable_slots,preferred_slots,max_daily_sessions\n"
    with pytest.raises(DataLoadError, match="teachers.csv has no rows"):
        draft_from_csv_files(files)


# --- Instance from draft validation tests ---

def test_instance_missing_draft_key():
    draft = load_sample("tiny")
    del draft["rooms"]
    with pytest.raises(DataLoadError, match="Draft is missing 'rooms'"):
        instance_from_draft(draft)


def test_instance_duplicate_teacher_id():
    draft = load_sample("tiny")
    draft["teachers"].append(copy.deepcopy(draft["teachers"][0]))
    with pytest.raises(DataLoadError, match="duplicate teacher_id 'T01'"):
        instance_from_draft(draft)


def test_instance_duplicate_room_id():
    draft = load_sample("tiny")
    draft["rooms"].append(copy.deepcopy(draft["rooms"][0]))
    with pytest.raises(DataLoadError, match="duplicate room_id 'R101'"):
        instance_from_draft(draft)


def test_instance_duplicate_course_id():
    draft = load_sample("tiny")
    draft["courses"].append(copy.deepcopy(draft["courses"][0]))
    with pytest.raises(DataLoadError, match="duplicate course_id 'FAI'"):
        instance_from_draft(draft)


def test_instance_duplicate_division_id():
    draft = load_sample("tiny")
    draft["divisions"].append(copy.deepcopy(draft["divisions"][0]))
    with pytest.raises(DataLoadError, match="duplicate division_id 'A'"):
        instance_from_draft(draft)


def test_instance_bad_slot_string():
    draft = load_sample("tiny")
    # 'Mon@09:30' is not a slot in tiny (slots are 09:00, 10:00, 11:00)
    draft["teachers"][0]["unavailable_slots"] = ["Mon@09:30"]
    with pytest.raises(DataLoadError, match=r"teachers\[T01\]\.unavailable_slots: 'Mon@09:30' is not a slot of the grid"):
        instance_from_draft(draft)


def test_instance_grid_validation():
    draft = load_sample("tiny")
    draft["days"] = ["Mon", "Mon"]
    with pytest.raises(DataLoadError, match="Duplicate day name 'Mon'"):
        instance_from_draft(draft)

    draft = load_sample("tiny")
    draft["slots"][1]["start"] = "11:00"
    draft["slots"][1]["end"] = "10:00"  # start >= end
    with pytest.raises(DataLoadError, match="must be earlier than end time"):
        instance_from_draft(draft)


def test_instance_fixed_assignment_errors():
    draft = load_sample("tiny")
    draft["fixed_assignments"] = [
        {"session_id": "FAI|A|1", "day_name": "Sunday", "start_time": "10:00", "room_id": "R101"}
    ]
    with pytest.raises(DataLoadError, match="fixed_assignments: unknown day_name 'Sunday'"):
        instance_from_draft(draft)

    draft["fixed_assignments"] = [
        {"session_id": "FAI|A|1", "day_name": "Mon", "start_time": "15:00", "room_id": "R101"}
    ]
    with pytest.raises(DataLoadError, match="fixed_assignments: unknown start_time '15:00'"):
        instance_from_draft(draft)

    draft["fixed_assignments"] = [
        {"session_id": "FAI|A|1", "day_name": "Mon", "start_time": "10:00", "room_id": "R101"},
        {"session_id": "FAI|A|1", "day_name": "Tue", "start_time": "10:00", "room_id": "R101"},
    ]
    with pytest.raises(DataLoadError, match="Duplicate fixed assignment for session 'FAI\\|A\\|1'"):
        instance_from_draft(draft)
