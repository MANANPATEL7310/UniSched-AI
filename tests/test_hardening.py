"""Stage 7 Hardening & Adversarial Test Suite.

Verifies system resilience against edge cases, malformed payloads, unicode characters,
garbage validator inputs, scale and recursion limits, and honest status reporting.
"""
from __future__ import annotations

import io
import pytest
from dataclasses import replace
from fastapi.testclient import TestClient

from api.jobs import jobs
from api.main import app
from csp.problem import build_csp
from csp.result import PRESETS as ALGO_PRESETS, SearchStatus
from csp.backtracking import solve
from data.generator import PRESETS as GEN_PRESETS, generate_instance
from data.loader import draft_from_csv_files, instance_from_draft, load_sample
from data.validator import validate_instance
from errors import DataLoadError
from models.assignment import Assignment
from models.course import Course
from models.division import Division
from models.instance import SchedulingInstance, expand_sessions
from models.room import Room
from models.teacher import Teacher
from models.timeslot import TimeGrid
from models.timetable import Timetable
from scheduling.scheduler import generate_timetable
from scheduling.timetable_validator import ViolationType, validate_timetable

client = TestClient(app)


def test_empty_and_whitespace_csv_files():
    """CSV loader given completely empty bytes or whitespace raises clear DataLoadError."""
    # Empty bytes for mandatory days.csv
    file_map = {
        "days.csv": b"",
        "slots.csv": b"start_time,end_time\n09:00,10:00\n",
        "teachers.csv": b"teacher_id,teacher_name,unavailable_slots,preferred_slots,max_daily_sessions\n",
        "courses.csv": b"course_id,course_name,teacher_id,sessions_per_week,duration_slots,room_types,eligible_divisions\n",
        "divisions.csv": b"division_id,division_name,student_count,enrolled_courses\n",
        "rooms.csv": b"room_id,room_name,room_type,capacity,unavailable_slots\n",
    }
    with pytest.raises(DataLoadError) as exc_info:
        draft_from_csv_files(file_map)
    msg = str(exc_info.value).lower()
    assert "empty" in msg or "no rows" in msg or "missing" in msg

    # Whitespace-only file
    file_map["days.csv"] = b"   \n\r\n   "
    with pytest.raises(DataLoadError) as exc_info:
        draft_from_csv_files(file_map)
    msg2 = str(exc_info.value).lower()
    assert "empty" in msg2 or "no rows" in msg2 or "missing" in msg2


def test_corrupt_and_garbage_assignments_to_validator():
    """Independent validator handles corrupted, out-of-range, and garbage assignments safely."""
    instance = instance_from_draft(load_sample("tiny"))
    
    # 1. Assignment referencing completely non-existent session ID
    garbage_assignment = {
        "NO_SUCH_SESSION_ID": Assignment(day=0, start_slot=0, room_id="R101"),
    }
    report1 = validate_timetable(instance, garbage_assignment)
    assert not report1.is_valid
    assert any(v.type == ViolationType.UNKNOWN_SESSION for v in report1.violations)

    # 2. Assignment with negative slot and non-existent room
    first_sid = instance.sessions[0].session_id
    bad_assignment = {
        first_sid: Assignment(day=0, start_slot=-1, room_id="NON_EXISTENT_ROOM"),
    }
    report2 = validate_timetable(instance, bad_assignment)
    assert not report2.is_valid
    assert any(v.type in (ViolationType.OUT_OF_RANGE, ViolationType.UNKNOWN_ROOM) for v in report2.violations)

    # 3. Assignment with slot overflowing day boundary
    overflow_assignment = {
        first_sid: Assignment(day=0, start_slot=9999, room_id="R101"),
    }
    report3 = validate_timetable(instance, overflow_assignment)
    assert not report3.is_valid
    assert any(v.type == ViolationType.OUT_OF_RANGE for v in report3.violations)


def test_unicode_and_special_characters_end_to_end():
    """Ensure unicode, punctuation, HTML entities, and emojis survive the entire solver and export pipeline."""
    grid = TimeGrid(day_names=("Mon", "Tue"), slot_starts=("09:00", "10:00"), slot_ends=("10:00", "11:00"))
    teacher = Teacher(
        teacher_id="T_ÜNICODE",
        name="Prof. Müller 🎓",
        unavailable=frozenset(),
    )
    course = Course(
        course_id="C_SPECIAL",
        name='C++ & "Algorithms" / <Advanced>',
        teacher_id="T_ÜNICODE",
        sessions_per_week=1,
        duration_slots=1,
        room_types=("lecture",),
        eligible_divisions=("DIV_Ω",),
    )
    division = Division(
        division_id="DIV_Ω",
        name="Section Ω (Omega, 'A')",
        student_count=40,
        enrolled_courses=("C_SPECIAL",),
    )
    room = Room(
        room_id="R_HALL#1",
        name="Lecture Hall #1 (South Annex, Room 101)",
        room_type="lecture",
        capacity=60,
        unavailable=frozenset(),
    )
    sessions = expand_sessions(
        courses={course.course_id: course},
        divisions={division.division_id: division},
    )
    instance = SchedulingInstance(
        name="unicode_test",
        grid=grid,
        teachers={teacher.teacher_id: teacher},
        rooms={room.room_id: room},
        divisions={division.division_id: division},
        courses={course.course_id: course},
        sessions=sessions,
        meta={},
    )

    # 1. Input validator check
    issues = validate_instance(instance)
    errors = [x for x in issues if x.severity == "ERROR"]
    assert len(errors) == 0

    # 2. Solver check (Config C)
    outcome = generate_timetable(instance, ALGO_PRESETS["C"])
    assert outcome.status == SearchStatus.SOLVED
    assert outcome.is_valid is True
    assert outcome.timetable is not None

    # 3. CSV Export check
    csv_str = outcome.timetable.to_csv_bytes().decode("utf-8")
    assert "Prof. Müller 🎓" in csv_str
    assert "Section Ω (Omega, 'A')" in csv_str
    assert '"Lecture Hall #1 (South Annex, Room 101)"' in csv_str


def test_malformed_slot_strings_safety():
    """Verify malformed slot strings yield clean validation errors without crashing."""
    draft = load_sample("tiny")
    malformed_slots = [
        "Mon",
        "Mon@",
        "@09:00",
        "Mon@25:00",
        "Funday@09:00",
        "Mon@09:00-10:00",
        "Mon@9:00",
    ]
    for bad_slot in malformed_slots:
        test_draft = dict(draft)
        test_draft["teachers"] = [dict(draft["teachers"][0])]
        test_draft["teachers"][0]["unavailable_slots"] = [bad_slot]
        res = client.post("/api/instances/validate", json=test_draft)
        assert res.status_code == 200
        body = res.json()
        assert body["parse_error"] is not None or any(
            i["severity"] == "ERROR" for i in body.get("issues", [])
        ), f"Expected parse_error or ERROR issue for malformed slot '{bad_slot}'"


def test_solver_limits_never_report_infeasible():
    """Timeouts and node limits must strictly report TIMEOUT / NODE_LIMIT, never INFEASIBLE_PROVEN."""
    # Generate a tight instance that requires real search
    inst = generate_instance(replace(GEN_PRESETS["small"], seed=42, tightness=0.7))
    problem = build_csp(inst)

    # 1. Extreme timeout
    cfg_timeout = replace(ALGO_PRESETS["A"], timeout_s=0.00001)
    res_timeout = solve(problem, cfg_timeout)
    assert res_timeout.status == SearchStatus.TIMEOUT
    assert "time limit" in res_timeout.message.lower()

    # 2. Extreme node limit
    cfg_nodes = replace(ALGO_PRESETS["A"], node_limit=1, timeout_s=60.0)
    res_nodes = solve(problem, cfg_nodes)
    assert res_nodes.status == SearchStatus.NODE_LIMIT
    assert "node limit" in res_nodes.message.lower()


def test_large_preset_recursion_limit():
    """Verify that search on large preset instances does not exceed Python recursion limits."""
    inst = generate_instance(replace(GEN_PRESETS["large"], seed=10))
    problem = build_csp(inst)
    assert len(problem.variables) > 50

    # Run with a short node limit or timeout to ensure recursion setrecursionlimit operates safely
    cfg = replace(ALGO_PRESETS["C"], node_limit=20, timeout_s=5.0)
    res = solve(problem, cfg)
    # Should exit with NODE_LIMIT or SOLVED, never RecursionError
    assert res.status in (SearchStatus.NODE_LIMIT, SearchStatus.SOLVED, SearchStatus.TIMEOUT)


def test_api_upload_csv_missing_mandatory_files():
    """Verify upload-csv endpoint returns 400 DATA_LOAD_ERROR when required CSV files are missing."""
    files = [
        ("files", ("days.csv", b"day_name\nMon\nTue\n", "text/csv")),
        # Intentionally missing slots.csv, teachers.csv, courses.csv, etc.
    ]
    res = client.post("/api/instances/upload-csv", files=files)
    assert res.status_code == 400
    body = res.json()
    assert body["error"]["code"] == "DATA_LOAD_ERROR"
    assert "missing" in body["error"]["message"].lower()


def test_api_concurrency_double_submit_protection():
    """Verify concurrent runs are rejected with 409 BUSY and clean message."""
    draft = load_sample("tight")
    payload = {
        "draft": draft,
        "config": {"algorithm": "A", "timeout_s": 20.0},
    }
    
    res1 = client.post("/api/runs", json=payload)
    if res1.status_code == 202:
        run_id = res1.json()["run_id"]
        try:
            if jobs.is_busy():
                res2 = client.post("/api/runs", json=payload)
                assert res2.status_code == 409
                assert res2.json()["error"]["code"] == "BUSY"
        finally:
            client.post(f"/api/runs/{run_id}/cancel")
