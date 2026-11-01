# Tight Instance

## Design Recipe
- 1 single lecture room (R101, capacity 60)
- 2 days x 3 slots = 6 total room-slots available
- Exactly 6 one-slot sessions required across 2 divisions (A with 3 courses, B with 3 courses)
- 3 teachers (T01, T02, T03) each assigned 2 sessions
- Interlocking teacher unavailable slots restrict each teacher to 4 available slots:
  - T01 unavailable Tue@09:00, Tue@10:00
  - T02 unavailable Mon@09:00, Mon@10:00
  - T03 unavailable Mon@11:00, Tue@11:00

## Solvability
- 100% capacity utilization.
- Admissible schedule example:
  - Mon@09:00 -> C05 (T03, Div B)
  - Mon@10:00 -> C06 (T03, Div B)
  - Mon@11:00 -> C01 (T01, Div A)
  - Tue@09:00 -> C03 (T02, Div A)
  - Tue@10:00 -> C04 (T02, Div B)
  - Tue@11:00 -> C02 (T01, Div A)

## Expected Outcome
- Status: **SOLVED**
