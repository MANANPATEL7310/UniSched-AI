# Tiny Instance

A minimal 5-session instance on a 2-day by 3-slot grid designed for initial end-to-end verification and fast unit testing.

## Dimensions
- **Days:** 2 (Mon, Tue)
- **Slots per day:** 3 (09:00, 10:00, 11:00) -> 6 total time slots
- **Rooms:** 3 (R101 [lecture, cap 60], R102 [lecture, cap 40], C101 [computer_lab, cap 60])
- **Teachers:** 3 (T01 [Dr. Rao], T02 [Dr. Sharma], T03 [Prof. Lee])
- **Divisions:** 2 (A [50 students], B [25 students])
- **Courses:** 3 (FAI [2 sessions/wk], MATH [1 session/wk], PLAB [1 session/wk])
- **Total Sessions:** 5 (`FAI|A|1`, `FAI|A|2`, `MATH|A|1`, `MATH|B|1`, `PLAB|A|1`)
- **Fixed Assignments:** `FAI|A|1` fixed at Mon 10:00 in R101

## Feasibility
Expected status: `SOLVED`.
A hand-verified valid placement is provided in `tests/fixtures/tiny_solution.json`.
