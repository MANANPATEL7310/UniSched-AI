# Impossible Instance

## Design Recipe
- 1 division (A, 50 students)
- 1 teacher (T01)
- 1 course (X), requiring 2 sessions per week (X|A|1, X|A|2)
- 2 rooms (R101, R102), capacity 60
- Time grid of 2 days x 2 slots = 4 slots (Mon@09:00, Mon@10:00, Tue@09:00, Tue@10:00)
- T01 is unavailable on 3 of the 4 slots: Mon@10:00, Tue@09:00, Tue@10:00.
- Therefore, T01 is available in ONLY ONE slot: Mon@09:00.

## Proof of Infeasibility (Pigeonhole Contradiction)
- Both sessions individually have non-empty initial unary domains:
  - Domain(X|A|1) = {(Mon, 09:00, R101), (Mon, 09:00, R102)} (size 2)
  - Domain(X|A|2) = {(Mon, 09:00, R101), (Mon, 09:00, R102)} (size 2)
- Root wipeout does NOT occur because neither domain is empty initially.
- However, assigning either session occupies T01 on Mon@09:00.
- Since a teacher cannot teach two sessions simultaneously, the second session has 0 legal placements remaining.
- By the pigeonhole principle (2 sessions into 1 teacher slot), no valid assignment can ever exist.

## Expected Outcome
- Status: **INFEASIBLE_PROVEN**
