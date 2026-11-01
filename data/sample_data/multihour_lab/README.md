# Multi-Hour Lab Instance

## Design Recipe
- 1 division (Division A, 35 students)
- 2 courses:
  - LAB: 2-slot duration, requires `computer_lab`
  - LEC: 1-slot duration, requires `lecture`
- 2 rooms:
  - C101: `computer_lab` (capacity 40, unavailable Mon@10:00)
  - R101: `lecture` (capacity 60, no unavailability)
- Time grid of 2 days x 4 slots: 09:00, 10:00, 11:00, 12:00.

## Consecutive-Slot Rules Tested
1. **Day Boundary:** A 2-slot session cannot start in slot 3 (12:00), because `start + duration = 3 + 2 = 5 > 4 slots per day`.
2. **Intermediate Unavailability:** C101 is unavailable at Mon@10:00 (slot 1).
   - If LAB starts at slot 0 (09:00), its occupied slots are {0, 1}, overlapping the unavailable slot 1 -> Illegal!
   - If LAB starts at slot 1 (10:00), its occupied slots are {1, 2}, overlapping the unavailable slot 1 -> Illegal!
   - Therefore on Monday, LAB can ONLY start at slot 2 (11:00, slots 2 and 3).
   - Alternatively, it can start on Tuesday at slots 0, 1, or 2.

## Expected Outcome
- Status: **SOLVED**
