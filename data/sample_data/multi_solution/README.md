# Multi-Solution Instance

## Design Recipe
- 2 divisions (A, B)
- 2 teachers (T01, T02)
- 2 courses (C01, C02), each with 1 session per week
- 4 rooms (R101, R102, R103, R104), capacity 60
- Time grid of 3 days (Mon, Tue, Wed) x 3 slots = 9 slots
- Total room-slots: 9 x 4 = 36 available coordinate assignments

## Exact Combinatorial Count
- Variable 1 (C01|A|1) can be placed in any of the 36 room-slots.
- Variable 2 (C02|B|1) has distinct teacher and division, so its only conflict is using the exact same room at the exact same slot.
- Thus, for every choice of C01, C02 has exactly 35 legal choices.
- Total valid solutions: `36 * 35 = 1,260`.

## Expected Outcome
- Status: **SOLVED**
