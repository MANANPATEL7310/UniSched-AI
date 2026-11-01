# Unavailability Instance

## Design Recipe
- 2 divisions (A, B)
- 2 courses (C01, C02), each 1 session
- 2 teachers (T01, T02)
- 2 rooms (R101, R102)
- Time grid of 2 days x 2 slots = 4 slots: Mon@09:00, Mon@10:00, Tue@09:00, Tue@10:00.

## Interlocking Reductions
1. **Teacher T01:** Unavailable on Mon@09:00, Tue@09:00, Tue@10:00 -> Only Mon@10:00 is available.
2. **Room R102:** Unavailable on Mon@10:00 -> C01 cannot use R102.
   - Therefore, C01 must be placed at `Mon@10:00 in R101`. Domain size is reduced to exactly 1.
3. **Teacher T02:** Unavailable on Mon@09:00, Mon@10:00, Tue@09:00 -> Only Tue@10:00 is available.
4. **Room R101:** Unavailable on Tue@10:00 -> C02 cannot use R101.
   - Therefore, C02 must be placed at `Tue@10:00 in R102`. Domain size is reduced to exactly 1.
5. Exactly one unique valid timetable exists.

## Expected Outcome
- Status: **SOLVED**
