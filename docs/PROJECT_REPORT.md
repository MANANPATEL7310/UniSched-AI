# University Class Timetabling via Classical Constraint Satisfaction Problems
## Foundations of Artificial Intelligence — Final Project Report

**Course:** Foundations of Artificial Intelligence (FAI)  
**System Name:** UniSched-AI  
**Repository:** [https://github.com/MANANPATEL7310/UniSched-AI.git](https://github.com/MANANPATEL7310/UniSched-AI.git)  
**Methodology:** Pure Symbolic Classical Constraint Satisfaction (Zero Machine Learning)

---

## 1. Executive Summary & Abstract

Timetabling in higher education is a computationally intractable combinatorial optimization problem classified as NP-complete. Standard heuristic approximations and machine learning models often suffer from statistical hallucinations, constraint violations, and an inability to mathematically prove infeasibility when resources are oversubscribed.

This project presents **UniSched-AI**, an end-to-end scheduling framework that models university course scheduling strictly as a classical **Constraint Satisfaction Problem (CSP)** $(X, D, C)$. We implemented four systematic search engines sharing a unified backtracking core:
1. **Config A:** Chronological depth-first backtracking baseline.
2. **Config B:** Backtracking enhanced with Minimum Remaining Values (MRV), Degree heuristic tie-breaking, and Least Constraining Value (LCV) heuristics.
3. **Config C:** Forward Checking (FC) with early domain wipeout detection.
4. **Config D:** Root Arc Consistency (AC-3) preprocessing combined with Maintaining Arc Consistency (MAC) throughout search.

To guarantee zero tolerance for invalid schedules, every solution is certified by an **independent interval-arithmetic validator** decoupled from the solver's internal occupancy structures. Across empirical evaluations spanning six hand-crafted benchmarks and synthetic planted instances up to large scale, Config C demonstrated superior real-time performance on loose to medium instances, while Config D proved capable of establishing mathematical infeasibility with **0 search node expansions** on tightly constrained contradictions.

---

## 2. Introduction & Problem Definition

Creating a viable university timetable requires allocating physical classrooms, specialized laboratories, faculty hours, and student cohorts to finite weekly time slots without resource double-booking.

### Hard Constraints
A generated schedule is valid if and only if **all** of the following hard constraints hold simultaneously:
1. **Faculty Non-Overlap:** No faculty member may teach more than one class session at the same time slot.
2. **Student Cohort Non-Overlap:** No student division may attend more than one lecture or lab simultaneously.
3. **Room Non-Overlap:** No physical classroom or laboratory may host more than one session in the same slot.
4. **Room Seating Capacity:** Classrooms must possess capacity greater than or equal to the enrolled student cohort size.
5. **Room Equipment Compatibility:** Laboratory sessions requiring specialized hardware (e.g., `computer_lab`) cannot be scheduled in standard lecture halls.
6. **Faculty Availability:** Sessions cannot be scheduled during a teacher's designated blackout windows.
7. **Room Availability:** Sessions cannot be placed during room maintenance or reserved intervals.
8. **Contiguous Multi-Slot Integrity:** 2-slot and 3-slot practicals must occupy consecutive slots on the same day without crossing daily boundaries.
9. **Fixed Session Pinnings:** Administrative pre-assignments must be strictly honored.

### Soft Optimization Criteria
Once hard feasibility is certified, quality is evaluated against secondary institutional preferences:
* Minimizing student gap hours (idle windows between classes).
* Balancing faculty daily workload (preventing daily overload).
* Fulfilling teacher preferred teaching hours.

---

## 3. Foundations of Artificial Intelligence (FAI) Mapping

### 3.1 The Intelligent Agent & PEAS Formulation

```
+-------------------------------------------------------------------------+
|                         UNISCHED-AI AGENT                               |
|                                                                         |
|  PERCEPTS / SENSORS                                                     |
|  - Academic Grid: Days D, Slots S                                       |
|  - Faculty, Course, Cohort, Classroom Specifications (CSV/JSON Drafts) |
|  - Search Config: Algorithms A-D, Timeouts, Node Limits                 |
|                               |                                         |
|                               v                                         |
|  DELIBERATIVE SEARCH ENGINE                                             |
|  - CSP Graph Representation (Variables X, Domains D, Occupancy Keys C)  |
|  - Systematic DFS Search + Dynamic Heuristics + Propagation Queues      |
|  - DomainState Trail (Reversible Backtrack Stack)                       |
|                               |                                         |
|                               v                                         |
|  ACTIONS / ACTUATORS                                                    |
|  - Certified Timetable Schedule (JSON/CSV)                              |
|  - Independent Interval Validation Audit Report (12 Categories)         |
|  - Empirical Search Metrics (Nodes, Attempts, Prunings, Runtimes)       |
+-------------------------------------------------------------------------+
```

* **Performance Measure ($P$):** 
  * 0 hard constraint violations (strict requirement).
  * Minimized search expansions (nodes, backtracks).
  * Sound, complete reporting of `INFEASIBLE_PROVEN` when unsatisfiable.
  * Minimized soft penalty scores.
* **Environment ($E$):** Discrete university timetable grid, student divisions, room capacities, course catalog.
* **Actuators ($A$):** Structured timetable assignment, validation report, progress callbacks.
* **Sensors ($S$):** CSV data tables, JSON API payloads, web UI form inputs.

### 3.2 Environment Properties

| Property | Classification | Technical Justification |
|---|---|---|
| **Observability** | **Fully Observable** | All courses, faculty availability, and room capacities are known prior to search. |
| **Determinism** | **Deterministic** | State transitions and domain filtering follow exact deterministic rules with strict tie-breaking. |
| **Dynamics** | **Static** | The problem instance does not change while the CSP solver executes. |
| **Continuity** | **Discrete** | Slots, days, rooms, and sessions are integer or categorical entities. |
| **Episodicity** | **Sequential** | Early variable assignments constrain the reachable domain values of future variables. |
| **Multi-Agent** | **Single-Agent** | The agent deliberates against a passive combinatorial constraint graph. |

---

## 4. System Architecture

UniSched-AI is built on a clean three-tier architecture ensuring strict separation of concerns:

```
[ Tier 1: Frontend SPA ]
  React 19 + TypeScript + Vite
  - Dashboard (FAI concepts, KPIs)
  - Data Management (Editable tables, availability grid)
  - Generate (Algorithm selector A-D, live progress, cancel)
  - Timetable Viewer (Interactive weekly grid, CSV export)
  - Constraint Validation (12-category violation breakdown)
  - Comparison (Multi-seed benchmark charts & tables)
              |
              | HTTP / REST (JSON)
              v
[ Tier 2: API & Orchestration ]
  FastAPI Service Layer (api/)
  - Background JobManager (Thread pool, cancel events, 409 BUSY guard)
  - Strict Pydantic Data Contracts & NaN-Safe Serializers
  - Single-Command SPA Static Server
              |
              | Pure Python In-Memory
              v
[ Tier 3: CSP Engine & Scheduling ]
  Pure Python Standard Library (csp/ & scheduling/)
  - CSP Graph & Occupancy Keys (constraints.py, problem.py)
  - Reversible Domain Trail (trail.py)
  - Search Core (backtracking.py, heuristics.py, forward_checking.py, ac3.py, mac.py)
  - Independent Interval Validator (scheduling/timetable_validator.py)
```

### Architectural Isolation Guarantees
* **Standard Library Engine:** The `csp/` package contains zero imports of `pandas`, `fastapi`, `pydantic`, or `matplotlib`. It relies exclusively on Python standard library data structures.
* **Independent Validator:** `scheduling/timetable_validator.py` shares zero code or data structures with `csp/`. Solutions must independently pass interval arithmetic checks.
* **Robust Threading:** Solver tasks execute in background daemon threads managed by `JobManager`. Long runs can be cancelled at any point via cooperative `threading.Event` checks.

---

## 5. Mathematical CSP Formulation

A classical CSP is formalized as $(X, D, C)$:

### Variables ($X$)
$$X = \{s_1, s_2, \dots, s_n\}$$
Each course $c$ requiring $k$ weekly sessions for division $d$ generates $k$ distinct variable instances:
$$s = \langle \text{course\_id}, \text{division\_id}, \text{teacher\_id}, \text{duration}, \text{index} \rangle$$

### Domains ($D$)
For each session $s$, domain $D(s)$ contains allowed tuples $v = (\text{day}, \text{slot}, \text{room})$ satisfying all unary rules:
$$\text{capacity}(\text{room}) \ge \text{size}(s.\text{division})$$
$$\text{type}(\text{room}) \in s.\text{room\_types}$$
$$\forall j \in [0, \text{duration}-1]: (\text{day}, \text{slot}+j) \notin \text{unavailable}(s.\text{teacher}) \cup \text{unavailable}(\text{room})$$
$$\text{slot} + \text{duration} \le S_{\text{slots\_per\_day}}$$

### Constraints ($C$) via Occupancy Keys
Binary non-overlap constraints are evaluated via set intersections:
$$\text{keys}(s, v) = \bigcup_{j=0}^{\text{duration}-1} \left\{ (\text{"T"}, s.\text{teacher}, d \cdot S + t + j), (\text{"D"}, s.\text{division}, d \cdot S + t + j), (\text{"R"}, r, d \cdot S + t + j) \right\}$$

Two assignments $v_a \in D(s_a)$ and $v_b \in D(s_b)$ conflict if and only if:
$$\text{keys}(s_a, v_a) \cap \text{keys}(s_b, v_b) \ne \emptyset$$

---

## 6. Algorithms & Search Strategies

### Config A — Baseline Chronological Backtracking
* Pure depth-first search exploring variables in lexicographical ID order.
* Values attempted in static domain order.
* Consistency checked on-the-fly against already assigned sessions.

### Config B — Dynamic Heuristics (MRV + Degree + LCV)
* **Variable Selection:**
  1. **Minimum Remaining Values (MRV):** Chooses $s = \arg\min |D_{\text{legal}}(s)|$.
  2. **Degree Heuristic:** Breaks MRV ties by selecting the variable with the highest degree in the unassigned constraint graph.
  3. **Lexicographical Tie-break:** Final ties resolved deterministically by session ID.
* **Value Selection (LCV):**
  * Evaluates candidate values by calculating how many values they eliminate from neighbor domains using precomputed key indices:
    $$\text{score}(s, v) = |\{(s', v') : s' \in \text{unassigned}, \, v' \in D(s'), \, \text{keys}(s, v) \cap \text{keys}(s', v') \ne \emptyset\}|$$
  * Evaluates values with smallest scores first.

### Config C — Forward Checking (FC)
* Assigning $X_i \leftarrow v$ triggers immediate pruning of all conflicting values in unassigned neighbors:
  $$\forall X_j \in \text{neighbors}(X_i): D(X_j) \leftarrow D(X_j) \setminus \{v' : \text{keys}(X_i, v) \cap \text{keys}(X_j, v') \ne \emptyset\}$$
* **Wipeout Fail-First:** If $|D(X_j)| = 0$ for any neighbor, the assignment immediately backtracks without deeper exploration.
* Checkpoints in `DomainState` allow reversible $O(k)$ trail unwinding.

### Config D — Root AC-3 + Maintaining Arc Consistency (MAC)
* **Root AC-3:** Executes queue-based AC-3 across all constraint arcs prior to search:
  * An arc $(X_i, X_j)$ is consistent if $\forall v_i \in D(X_i), \exists v_j \in D(X_j)$ such that $v_i$ and $v_j$ are compatible.
  * Values lacking support are pruned. If $D(X_i) = \emptyset$, infeasibility is proven before expanding any search nodes.
* **MAC Search:** After assigning $X_i \leftarrow v$, FC prunes immediate neighbors, and all modified neighbors enqueue directional arcs to propagate multi-hop transitive deductions.

---

## 7. Dual Validation Strategy

To prevent solver self-confirmation bias, solutions are validated twice using fundamentally distinct algorithms:

| Validation Layer | Engine Internal Check | Independent Validator (`scheduling/timetable_validator.py`) |
|---|---|---|
| **Mathematical Basis** | Discrete Occupancy Key Set Intersections | 1D Real Interval Arithmetic Overlaps |
| **Execution Point** | During search at every assignment step | Post-search upon candidate solution generation |
| **Scope** | Binary resource conflicts | 12 Hard Constraint Categories (Capacity, Room Types, Unavailabilities, Contiguous Durations, Day Overflows, Duplicate/Missing Sessions) |
| **Code Isolation** | Inside `csp/` package | Inside `scheduling/` package (zero `csp/` imports) |

A solution is certified as `VALID` in the UI and report if and only if the independent validator returns `is_valid == True`.

---

## 8. Empirical Evaluation & Benchmark Results

### 8.1 Benchmark Dataset Characteristics
1. **`tiny`:** 5 sessions, 2 days $\times$ 3 slots, 3 rooms. Hand-solved verification benchmark.
2. **`feasible_obvious`:** 2 sessions, loose constraints.
3. **`impossible`:** 2 sessions competing for 1 resource with 0 alternative slots. Unsat benchmark.
4. **`tight`:** 6 sessions, packed schedule with near-full utilization.
5. **`multihour_lab`:** Consecutive multi-slot lab sessions testing contiguous slot allocation without day-boundary overflow.
6. **`unavailability`:** Complex teacher and room blackout windows.
7. **Synthetic Presets:** Planted-solution generator instances (`small`: ~36 sessions, `medium`: ~80 sessions, `large`: ~160 sessions).

### 8.2 Experimental Results Across Named Instances

| Instance | Expected Status | Config A (Nodes) | Config B (Nodes) | Config C (Nodes) | Config D (Nodes) | Certified Valid |
|---|---|:---:|:---:|:---:|:---:|:---:|
| `feasible_obvious` | `SOLVED` | 3 | 3 | 3 | 3 | **Yes** |
| `impossible` | `INFEASIBLE_PROVEN` | 3 | 3 | 1 | **0 (AC-3 wipeout)** | **Yes** |
| `multi_solution` | `SOLVED` | 3 | 3 | 3 | 3 | **Yes** |
| `multihour_lab` | `SOLVED` | 3 | 3 | 3 | 3 | **Yes** |
| `tight` | `SOLVED` | 11 (4 backtracks) | 7 (0 backtracks) | 7 (0 backtracks) | 7 (0 backtracks) | **Yes** |
| `tiny` | `SOLVED` | 6 | 6 | 6 | 6 | **Yes** |
| `unavailability` | `SOLVED` | 3 | 3 | 3 | 3 | **Yes** |

### 8.3 Synthetic Matrix Benchmark Results (`small` preset, 36 sessions)

Data collected from direct execution run (`results/20261101_141003.csv`):

| Algorithm Preset | Status | Solved? | Runtime (s) | Search Nodes | Search Attempts | Backtracks | Values Pruned | Consistency Checks |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Config A (Baseline)** | `SOLVED` | True | 0.00027s | 37 | 515 | 0 | 0 | 515 |
| **Config B (Heuristics)** | `SOLVED` | True | 0.01122s | 37 | 36 | 0 | 0 | 47,967 |
| **Config C (Forward Checking)** | `SOLVED` | True | 0.00417s | 37 | 36 | 0 | 660 | 36 |
| **Config D (Root AC-3 + MAC)** | `SOLVED` | True | 0.07447s | 37 | 36 | 0 | 660 | 344,256 |

```
                       BENCHMARK COMPARISON CHART (SMALL PRESET)
                       
  Search Attempts:
  Config A | ################################################## 515
  Config B | #### 36
  Config C | #### 36
  Config D | #### 36
  
  Values Pruned via Propagation:
  Config A | 0
  Config B | 0
  Config C | ############################## 660
  Config D | ############################## 660
```

---

## 9. Discussion & Comparative Findings

1. **Impact of MRV & LCV on Search Attempts:**
   * On the 36-session synthetic instance, baseline chronological backtracking (Config A) required **515 value assignment attempts** to navigate past initial collisions.
   * Applying MRV and LCV (Config B) reduced attempts to exactly **36** (1 attempt per session, meaning the heuristic made the optimal choice on the first attempt at every depth level).

2. **The Trade-Off of Heuristic and AC-3 Overhead:**
   * While Config B reduced attempts dramatically, computing LCV scores required **47,967 consistency checks**.
   * Forward Checking (Config C) proved to be the sweet spot: by pruning 660 invalid values from neighbor domains upon assignment, it required only **36 consistency checks**, yielding a faster wall-clock runtime than Config B.
   * MAC (Config D) incurred substantial revision overhead (344,256 checks) on loose instances where higher-order arc consistency found no additional prunings beyond forward checking.

3. **Infeasibility Detection via AC-3:**
   * On the `impossible` benchmark, Config A and B had to expand search nodes and backtrack to prove that no valid schedule exists.
   * Config C detected the domain wipeout after 1 node expansion.
   * Config D achieved an immediate unsat proof with **0 search nodes** during root AC-3 preprocessing, proving that arc consistency is immensely powerful on tightly constrained contradictions.

---

## 10. Limitations & Edge Cases

1. **Large Problem Scale & Asymmetric Constraints:**
   * On instances with >250 sessions and high tightness (>0.85), MAC queue revisions scale quadratically with graph density. When memory or timeouts occur, the solver honestly returns `TIMEOUT` or `NODE_LIMIT`, refusing to misreport incompleteness as infeasibility.
2. **Pure Satisfiability Focus:**
   * The core engine is an exact constraint satisfaction engine. While soft penalties (student gaps, faculty preferences) are evaluated and reported, the search does not perform branch-and-bound optimization across all valid solutions.

---

## 11. Stage 6 Advanced Extensions (Implemented)

To bridge the gap between static satisfiability and live real-world administrative operations, the system includes three advanced algorithmic extensions:

### 11.1 Minimal-Change Dynamic Rescheduling Engine (`scheduling/rescheduler.py`)
When unanticipated operational disruptions occur (e.g. sudden faculty sickness or laboratory equipment failure at a specific day/slot), the rescheduler calculates an updated conflict-free timetable while minimizing perturbation to existing schedules:
1. **Disruption Injection:** Accepts targeted perturbations (`TeacherUnavailableChange` or `RoomUnavailableChange`).
2. **Locking Policies & Progressive Relaxation:**
   * **Strict:** Freezes all unaffected sessions (`fixed = old_assignment`); only directly conflicted sessions are free to move.
   * **Relax Neighbors (Progressive Rings):** If the strict problem is provably infeasible (`INFEASIBLE_PROVEN`), the engine automatically unfreezes the resource-sharing neighborhood (Ring 1: sessions sharing teacher/division/room; Ring 2: secondary neighbors) until a feasible repair is discovered.
   * **Free:** All sessions are free to move, but distance heuristics prioritize preserving old positions.
3. **Disruption Distance Metric:** Domain values for free sessions are ordered by ascending disruption distance:
   $$\text{dist}(v, v_{old}) = \langle \mathbb{I}[day \neq day_{old}], |slot - slot_{old}|, \mathbb{I}[room \neq room_{old}] \rangle$$
4. **Validation & Diff:** Computes a full session-by-session diff table and guarantees 0 hard conflicts via independent validation before publication.

### 11.2 Soft-Constraint Local Optimization (`scheduling/soft_improvement.py`)
Using hill-climbing local search and Min-Conflicts style value reassignments, this module optimizes secondary preferences (faculty gaps, division gaps, room stability) on top of an already valid timetable:
* Evaluates single-session slot/room relocations and equal-duration pair swaps.
* **Invariant:** Every proposed state change is verified by `validate_timetable`. A move is accepted if and only if hard constraint violations remain zero and total soft penalty strictly decreases.

### 11.3 Search Tree Tracing (`csp/search_trace.py`)
A telemetry hook recording discrete search events (`SELECT_VAR`, `TRY_VALUE`, `ASSIGN`, `PRUNE`, `WIPEOUT`, `BACKTRACK`) with depth and context notes, capped at 2,000 events to maintain zero overhead during standard benchmarking runs.

---

## 12. Conclusion

UniSched-AI demonstrates that classical, symbolic Artificial Intelligence provides a mathematically rigorous, explainable, and 100% reliable framework for university course timetabling. By framing timetabling as a CSP with occupancy key representations, implementing multiple propagation regimes (Baseline, Heuristic, Forward Checking, MAC), and augmenting the solver with minimal-change repair and an independent interval validator, the system eliminates the constraint violations and hallucinations inherent in machine learning approaches.

---

## References

1. Russell, S., & Norvig, P. (2020). *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson. (Chapters 3, 6: Constraint Satisfaction Problems).
2. Mackworth, A. K. (1977). Consistency in networks of relations. *Artificial Intelligence*, 8(1), 99-118.
3. Haralick, R. M., & Elliott, G. L. (1980). Increasing tree search efficiency for constraint satisfaction problems. *Artificial Intelligence*, 14(3), 263-313.
4. Burke, E. K., & Petrovic, S. (2002). Recent research directions in automated timetabling. *European Journal of Operational Research*, 140(2), 266-280.

