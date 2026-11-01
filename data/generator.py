"""Synthetic instance generator with planted-solution feasibility guarantee."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Mapping

from errors import GenerationError
from models.course import Course
from models.division import Division
from models.instance import SchedulingInstance, expand_sessions
from models.room import Room
from models.teacher import Teacher
from models.timeslot import TimeGrid


@dataclass(frozen=True)
class GeneratorConfig:
    """Configuration parameters for generating synthetic scheduling instances."""

    name: str = "generated"
    num_days: int = 5
    slots_per_day: int = 6
    num_divisions: int = 3
    num_teachers: int = 4
    num_courses: int = 6
    num_rooms: int = 4
    sessions_per_course: tuple[int, int] = (1, 3)     # inclusive range per course
    lab_fraction: float = 0.2                          # share of courses that are 2-slot labs
    availability_density: float = 0.3                  # share of FREE slots turned into unavailable slots
    tightness: float = 0.5                             # 0..1 target utilisation of room-slots
    seed: int = 0


PRESETS: dict[str, GeneratorConfig] = {
    "small": GeneratorConfig(
        name="small",
        num_days=5,
        slots_per_day=6,
        num_divisions=3,
        num_teachers=4,
        num_courses=6,
        num_rooms=4,
        sessions_per_course=(1, 3),
        lab_fraction=0.2,
        availability_density=0.3,
        tightness=0.5,
        seed=42,
    ),
    "medium": GeneratorConfig(
        name="medium",
        num_days=5,
        slots_per_day=8,
        num_divisions=6,
        num_teachers=10,
        num_courses=12,
        num_rooms=8,
        sessions_per_course=(1, 3),
        lab_fraction=0.2,
        availability_density=0.3,
        tightness=0.5,
        seed=42,
    ),
    "large": GeneratorConfig(
        name="large",
        num_days=5,
        slots_per_day=8,
        num_divisions=12,
        num_teachers=20,
        num_courses=24,
        num_rooms=14,
        sessions_per_course=(1, 3),
        lab_fraction=0.2,
        availability_density=0.3,
        tightness=0.5,
        seed=42,
    ),
}


def generate_instance(cfg: GeneratorConfig) -> SchedulingInstance:
    """Generate a valid scheduling instance with a guaranteed planted solution."""
    rng = random.Random(cfg.seed)

    # 1. Grid
    day_names = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[:cfg.num_days]
    slot_starts = tuple(f"{9 + s:02d}:00" for s in range(cfg.slots_per_day))
    slot_ends = tuple(f"{10 + s:02d}:00" for s in range(cfg.slots_per_day))
    grid = TimeGrid(day_names=day_names, slot_starts=slot_starts, slot_ends=slot_ends)

    # 2. Divisions
    div_defs: list[tuple[str, int]] = []
    for i in range(cfg.num_divisions):
        did = chr(ord("A") + i) if i < 26 else f"DIV_{i+1:02d}"
        size = rng.randint(30, 70)
        div_defs.append((did, size))
    max_div_size = max(size for _, size in div_defs)

    # 3. Rooms
    num_lectures = max(1, int(round(0.6 * cfg.num_rooms)))
    num_labs = cfg.num_rooms - num_lectures
    if cfg.lab_fraction > 0 and num_labs == 0 and cfg.num_rooms >= 2:
        num_lectures = cfg.num_rooms - 1
        num_labs = 1

    room_types: list[str] = []
    for _ in range(num_lectures):
        room_types.append("lecture")
    for i in range(num_labs):
        if cfg.lab_fraction > 0:
            room_types.append("computer_lab" if i % 2 == 0 else "general_lab")
        else:
            room_types.append("lecture")

    capacities = [rng.choice([30, 40, 60, 80]) for _ in range(cfg.num_rooms)]

    # Ensure for each room type present, at least one room can hold the largest division
    for rt in set(room_types):
        matching = [i for i, t in enumerate(room_types) if t == rt]
        if matching:
            max_idx = max(matching, key=lambda i: capacities[i])
            if capacities[max_idx] < max_div_size:
                capacities[max_idx] = max_div_size + 10

    # Ensure ample large rooms so division size doesn't artificially bottleneck planting
    for i in range(cfg.num_rooms):
        if capacities[i] < max_div_size and rng.random() < 0.6:
            capacities[i] = max_div_size + 10

    rooms: dict[str, Room] = {}
    for i in range(cfg.num_rooms):
        rid = f"R{i+1:02d}"
        rooms[rid] = Room(
            room_id=rid,
            name=f"Room {rid}",
            room_type=room_types[i],
            capacity=capacities[i],
            unavailable=frozenset(),
        )

    # 4. Teachers
    teachers: dict[str, Teacher] = {}
    for i in range(cfg.num_teachers):
        tid = f"T{i+1:02d}"
        teachers[tid] = Teacher(teacher_id=tid, name=f"Teacher {tid}")

    # 5. Courses
    lab_types = tuple(sorted({r.room_type for r in rooms.values() if "lab" in r.room_type}))
    if not lab_types:
        lab_types = ("lecture",)

    num_labs_courses = int(round(cfg.lab_fraction * cfg.num_courses))
    course_meta: list[dict] = []
    for i in range(cfg.num_courses):
        cid = f"C{i+1:02d}"
        is_lab = (i < num_labs_courses) and (cfg.lab_fraction > 0)
        duration = 2 if is_lab else 1
        r_types = lab_types if is_lab else ("lecture",)
        tid = f"T{(i % cfg.num_teachers) + 1:02d}"
        spw = rng.randint(cfg.sessions_per_course[0], cfg.sessions_per_course[1])
        course_meta.append({
            "cid": cid,
            "tid": tid,
            "duration": duration,
            "room_types": r_types,
            "spw": spw,
        })

    # 6. Connect divisions and courses
    div_courses: dict[str, set[str]] = {did: set() for did, _ in div_defs}
    all_cids = [c["cid"] for c in course_meta]
    min_enrol = min(3, len(all_cids))

    for did, _ in div_defs:
        sampled = rng.sample(all_cids, min_enrol)
        div_courses[did].update(sampled)

    # Ensure every course is enrolled by at least one division
    enrolled_cids = {c for cset in div_courses.values() for c in cset}
    for cid in all_cids:
        if cid not in enrolled_cids:
            random_did = rng.choice(list(div_courses.keys()))
            div_courses[random_did].add(cid)

    # Balance tightness target
    total_slots = cfg.num_days * cfg.slots_per_day
    total_room_slots = cfg.num_rooms * total_slots
    target_hours = int(round(cfg.tightness * total_room_slots))
    max_div_hours = int(0.68 * total_slots)

    c_map = {c["cid"]: c for c in course_meta}
    def calc_hours() -> int:
        return sum(c_map[cid]["spw"] * c_map[cid]["duration"] for d in div_courses.values() for cid in d)

    def div_hours(did: str) -> int:
        return sum(c_map[cid]["spw"] * c_map[cid]["duration"] for cid in div_courses[did])

    all_pairs = [(did, cid) for did in div_courses for cid in all_cids if cid not in div_courses[did]]
    rng.shuffle(all_pairs)
    for did, cid in all_pairs:
        if calc_hours() >= target_hours:
            break
        pair_hrs = c_map[cid]["spw"] * c_map[cid]["duration"]
        if div_hours(did) + pair_hrs <= max_div_hours:
            div_courses[did].add(cid)

    # Build final Course and Division instances
    courses: dict[str, Course] = {}
    for c in course_meta:
        cid = c["cid"]
        elig = tuple(sorted(did for did, cset in div_courses.items() if cid in cset))
        courses[cid] = Course(
            course_id=cid,
            name=f"Course {cid}",
            teacher_id=c["tid"],
            sessions_per_week=c["spw"],
            duration_slots=c["duration"],
            room_types=c["room_types"],
            eligible_divisions=elig,
        )

    divisions: dict[str, Division] = {}
    for did, size in div_defs:
        divisions[did] = Division(
            division_id=did,
            name=f"Division {did}",
            student_count=size,
            enrolled_courses=tuple(sorted(div_courses[did])),
        )

    sessions = expand_sessions(courses, divisions)

    # 7. Plant solution using randomized search with up to 50 attempts
    plant: dict[str, tuple[int, int, str]] | None = None
    all_room_ids = list(rooms.keys())

    for attempt in range(50):
        occupied_teacher: set[tuple[str, int, int]] = set()
        occupied_division: set[tuple[str, int, int]] = set()
        occupied_room: set[tuple[str, int, int]] = set()
        current_plant: dict[str, tuple[int, int, str]] = {}
        unassigned = list(sessions)
        failed = False

        while unassigned:
            # Order unassigned sessions by MRV (fewest candidate placements)
            best_session = None
            best_cands: list[tuple[int, int, str]] | None = None

            for s in unassigned:
                dur = s.duration_slots
                tid = s.teacher_id
                did = s.division_id
                cands: list[tuple[int, int, str]] = []

                for d in range(cfg.num_days):
                    for slot in range(cfg.slots_per_day - dur + 1):
                        if any(
                            (tid, d, slot + off) in occupied_teacher
                            or (did, d, slot + off) in occupied_division
                            for off in range(dur)
                        ):
                            continue
                        for rid in all_room_ids:
                            rm = rooms[rid]
                            if rm.room_type not in s.room_types or rm.capacity < s.required_capacity:
                                continue
                            if any((rid, d, slot + off) in occupied_room for off in range(dur)):
                                continue
                            cands.append((d, slot, rid))

                if len(cands) == 0:
                    failed = True
                    break

                if best_cands is None or len(cands) < len(best_cands):
                    best_session = s
                    best_cands = cands
                    if len(cands) == 1:
                        break

            if failed or best_session is None or not best_cands:
                failed = True
                break

            chosen = rng.choice(best_cands)
            d, slot, rid = chosen
            dur = best_session.duration_slots
            tid = best_session.teacher_id
            did = best_session.division_id

            current_plant[best_session.session_id] = chosen
            unassigned.remove(best_session)

            for off in range(dur):
                occupied_teacher.add((tid, d, slot + off))
                occupied_division.add((did, d, slot + off))
                occupied_room.add((rid, d, slot + off))

        if not failed:
            plant = current_plant
            break

    if plant is None:
        raise GenerationError("Too tight: reduce sessions or tightness")

    # 8. Availability derived from plant
    all_grid_slots = [(d, s) for d in range(cfg.num_days) for s in range(cfg.slots_per_day)]
    for tid, teacher in list(teachers.items()):
        teacher_occupied = {(d, s) for (t, d, s) in occupied_teacher if t == tid}
        free = [slot for slot in all_grid_slots if slot not in teacher_occupied]
        k = int(round(cfg.availability_density * len(free)))
        unav = frozenset(rng.sample(free, k)) if free and k > 0 else frozenset()
        teachers[tid] = Teacher(
            teacher_id=tid,
            name=teacher.name,
            unavailable=unav,
            preferred=teacher.preferred,
            max_daily_sessions=teacher.max_daily_sessions,
        )

    for rid, room in list(rooms.items()):
        room_occupied = {(d, s) for (r, d, s) in occupied_room if r == rid}
        free = [slot for slot in all_grid_slots if slot not in room_occupied]
        k = int(round(cfg.availability_density * len(free)))
        unav = frozenset(rng.sample(free, k)) if free and k > 0 else frozenset()
        rooms[rid] = Room(
            room_id=rid,
            name=room.name,
            room_type=room.room_type,
            capacity=room.capacity,
            unavailable=unav,
        )

    meta = {
        "planted_solution": {sid: list(coord) for sid, coord in plant.items()},
        "generator_config": asdict(cfg),
        "num_sessions": len(sessions),
    }

    return SchedulingInstance(
        name=cfg.name,
        grid=grid,
        teachers=teachers,
        rooms=rooms,
        divisions=divisions,
        courses=courses,
        sessions=sessions,
        meta=meta,
    )

