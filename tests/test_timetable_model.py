"""Unit tests for models/timetable.py (Timetable and Entry)."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from data.loader import load_sample, instance_from_draft
from models.assignment import Assignment
from models.timetable import Entry, Timetable


@pytest.fixture
def tiny_timetable() -> Timetable:
    draft = load_sample("tiny")
    instance = instance_from_draft(draft)
    data = json.loads(Path("tests/fixtures/tiny_solution.json").read_text(encoding="utf-8"))
    assignments = {
        sid: Assignment(day=v[0], start_slot=v[1], room_id=v[2])
        for sid, v in data["assignments"].items()
    }
    return Timetable(instance, assignments)


def test_timetable_entries_and_sorting(tiny_timetable):
    entries = tiny_timetable.entries()
    assert len(entries) == 5

    # Check that entries are sorted by (day, start_slot, room_id, session_id)
    keys = [(e.day, e.start_slot, e.room_id, e.session_id) for e in entries]
    assert keys == sorted(keys)

    # Check entry content
    first = entries[0]
    assert isinstance(first, Entry)
    assert first.day_name in ("Mon", "Tue")
    assert first.course_name != ""
    assert first.teacher_name != ""
    assert first.division_name != ""
    assert first.room_name != ""
    assert first.duration_slots >= 1
    assert first.end_slot == first.start_slot + first.duration_slots - 1


def test_timetable_views(tiny_timetable):
    all_entries = tiny_timetable.view("all")
    assert len(all_entries) == 5

    div_a_entries = tiny_timetable.view("division", "A")
    assert len(div_a_entries) == 4
    assert all(e.division_id == "A" for e in div_a_entries)

    t01_entries = tiny_timetable.view("teacher", "T01")
    assert len(t01_entries) == 2
    assert all(e.teacher_id == "T01" for e in t01_entries)

    r101_entries = tiny_timetable.view("room", "R101")
    assert len(r101_entries) == 3
    assert all(e.room_id == "R101" for e in r101_entries)

    fai_entries = tiny_timetable.view("course", "FAI")
    assert len(fai_entries) == 2
    assert all(e.course_id == "FAI" for e in fai_entries)

    with pytest.raises(ValueError, match="Unknown view kind 'unknown_kind'"):
        tiny_timetable.view("unknown_kind", "X")


def test_timetable_dataframe_export(tiny_timetable):
    df = tiny_timetable.to_dataframe()
    expected_cols = [
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
    assert list(df.columns) == expected_cols
    assert len(df) == 5


def test_timetable_csv_bytes(tiny_timetable):
    csv_bytes = tiny_timetable.to_csv_bytes()
    assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    text = csv_bytes.decode("utf-8-sig")
    lines = text.strip().splitlines()
    assert len(lines) == 6  # 1 header + 5 rows
    header = lines[0].split(",")
    assert header[0] == "Day"
    assert header[-1] == "Session ID"


def test_timetable_json_roundtrip(tiny_timetable):
    d = tiny_timetable.to_json_dict()
    assert d["instance_name"] == "tiny"
    assert len(d["assignments"]) == 5

    rebuilt = Timetable.from_json_dict(tiny_timetable.instance, d)
    assert rebuilt.assignment == tiny_timetable.assignment
    assert len(rebuilt.entries()) == 5
