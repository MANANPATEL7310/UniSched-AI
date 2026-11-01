# UniSched-AI — University Timetable Scheduler via Classical CSP

An end-to-end, deterministic university course timetable scheduling system powered by **classical Constraint Satisfaction Problem (CSP)** algorithms and **symbolic Artificial Intelligence**. Built with a pure Python CSP engine, a FastAPI service layer, and an interactive React + TypeScript frontend.

---

## 🚫 No-Machine-Learning Statement

> **Fundamental Principle:** This project uses **zero machine learning**, zero neural networks, and zero training datasets. It relies on no external black-box optimization solvers (no OR-Tools, CP-SAT, PuLP, or Gurobi).
>
> All scheduling is framed strictly as an exact **Constraint Satisfaction Problem $(X, D, C)$** solved using classical depth-first search, variable/value heuristics (MRV, Degree, LCV), and constraint propagation algorithms (Forward Checking, AC-3, MAC). Every result is deterministic, verifiable, and explainable.

---

## 🏛️ Problem Formulation

University course timetabling requires assigning each scheduled class session to an absolute time slot and physical classroom such that all hard institutional rules are strictly satisfied.

### The CSP Model: $(X, D, C)$

1. **Variables ($X$):**
   * One variable per scheduled class session: $X = \{s_1, s_2, \dots, s_n\}$.
   * Sessions have a defined duration $k \in \{1, 2, 3\}$ slots, an assigned teacher, an enrolled student division, and allowable room types.

2. **Domains ($D$):**
   * For each session $s$, $D(s)$ is the ordered set of valid candidate assignments $v = (\text{day}, \text{start\_slot}, \text{room})$.
   * Filtered initially by **unary constraints**:
     * Room capacity $\ge$ student division size.
     * Room type matches course requirement (`lecture`, `lab`, `seminar`).
     * Teacher and room availability (cannot be assigned to unavailable slots).
     * Day boundary constraint (a multi-hour session cannot cross midnight or overflow the day).
     * Fixed pre-assignments (if specified, domain is pinned to that exact slot and room).

3. **Constraints ($C$) via Occupancy Keys:**
   * Binary non-overlapping constraints are modeled compactly using **occupancy keys**:
     $$\text{keys}(s, v) = \bigcup_{j=0}^{k-1} \left\{ (\text{"T"}, \text{teacher\_id}, \text{slot} + j), (\text{"D"}, \text{division\_id}, \text{slot} + j), (\text{"R"}, \text{room\_id}, \text{slot} + j) \right\}$$
   * **Rule:** Two assignments conflict if and only if their key sets intersect:
     $$\text{keys}(s_1, v_1) \cap \text{keys}(s_2, v_2) \ne \emptyset$$
   * This covers teacher double-booking, division overlapping classes, room collisions, and multi-slot duration blocks with $O(1)$ set intersection checks.

4. **Independent Interval Validator:**
   * An independent validation module (`scheduling/timetable_validator.py`) inspects solutions using interval arithmetic, completely decoupled from the CSP occupancy keys. Every solution is validated against 12 distinct violation checks.

---

## ⚡ Search Algorithms (Configs A–D)

The engine implements four progressive classical search configurations sharing a single backtracking core:

| Config | Algorithm | Variable Heuristic | Value Heuristic | Propagation | Purpose & Characteristics |
|:---:|---|---|---|---|---|
| **A** | **Baseline Backtracking** | Static chronological order | Domain order | None | Pure depth-first search baseline. Serves as ground truth for node expansion comparisons. |
| **B** | **Backtracking + Heuristics** | **MRV** (Minimum Remaining Values) + **Degree** tie-breaker | **LCV** (Least Constraining Value) | None | Prunes search breadth by failing fast on tight variables and choosing values that leave maximum flexibility for neighbors. |
| **C** | **Forward Checking (FC)** | MRV + Degree + ID tie-break | LCV | **Forward Checking** | After assigning variable $X_i$, immediately prunes conflicting values from unassigned neighbors. Detects domain wipeouts early without exploring deeper subtrees. |
| **D** | **Root AC-3 + MAC** | MRV + Degree + ID tie-break | LCV | **Root AC-3** + **MAC** | Pre-processes domains with AC-3 before search begins; maintains full arc consistency (MAC) via queue-based propagation after every search assignment. Capable of proving unsat with **0 search nodes** on tight contradictions. |

---

## 📁 Repository Structure

```
.
├── api/                        # FastAPI REST API layer
│   ├── jobs.py                 # Background thread JobManager (concurrency, TTL, cancel)
│   ├── main.py                 # App entrypoint, CORS, exception handlers, SPA static mount
│   ├── routers/                # Endpoints (/samples, /instances, /runs, /generator, /benchmarks)
│   ├── schemas.py              # Pydantic input models and request contracts
│   └── serializers.py          # DTO converters ensuring NaN-free, sanitized JSON
├── csp/                        # Pure CSP Solver Engine (Standard Library Only)
│   ├── ac3.py                  # AC-3 arc consistency preprocessor and revision logic
│   ├── backtracking.py         # Universal depth-first search core with limit enforcement
│   ├── constraints.py          # Unary filters and occupancy key generators
│   ├── domains.py              # Domain builder for scheduling variables
│   ├── forward_checking.py     # Forward checking propagation and wipeout detection
│   ├── heuristics.py           # MRV, Degree, and LCV heuristic implementations
│   ├── mac.py                  # Maintaining Arc Consistency (MAC) search propagation
│   ├── problem.py              # CSPProblem graph, adjacency lists, and neighbor indexing
│   ├── result.py               # SearchStatus, SearchConfig, and SearchMetrics types
│   └── trail.py                # DomainState trail for deterministic checkpoint/restore
├── data/                       # Data management, loaders, schemas, and instances
│   ├── generator.py            # Synthetic problem instance generator with planted solutions
│   ├── loader.py               # Draft ⇄ SchedulingInstance converters & CSV parsers
│   ├── sample_data/            # Six hand-crafted named instances + presets documentation
│   ├── schemas.py              # CSV column schemas and data structures
│   └── validator.py            # Comprehensive pre-flight input validator (17 distinct rules)
├── evaluation/                 # Benchmarking and reporting tools
│   ├── benchmarks.py           # Multi-seed matrix benchmark runner with progress tracking
│   ├── metrics.py              # Performance metric collection and statistics
│   └── reports.py              # Automated matplotlib chart generation (runtime, nodes, backtracks)
├── frontend/                   # React 19 + TypeScript Single Page Application (SPA)
│   ├── src/components/         # Layout, StatusBanner, WeekGrid, EditableTable, AvailabilityGrid
│   ├── src/pages/              # Dashboard, DataManagement, Generate, Viewer, Validation, Comparison
│   ├── src/lib/                # Week grid layout engine, colors, explanations, status reducer
│   └── src/tests/              # Comprehensive Vitest component and accessibility test suite
├── models/                     # Shared immutable domain dataclasses
│   ├── assignment.py           # Assignment(day, start_slot, room_id)
│   ├── course.py               # Course definition and eligibility
│   ├── division.py             # Student division / cohort
│   ├── instance.py             # SchedulingInstance root model
│   ├── room.py                 # Physical classroom / lab specifications
│   ├── session.py              # ClassSession expanded variable
│   ├── teacher.py              # Faculty member constraints
│   ├── timetable.py            # Solution Timetable, Entry formatting, and CSV export
│   └── timeslot.py             # TimeGrid slot definitions
├── scheduling/                 # Scheduling facade and independent validators
│   ├── scheduler.py            # generate_timetable facade and background RunHandle
│   ├── soft_constraints.py     # Soft constraint evaluators (gaps, workload balance, preferences)
│   └── timetable_validator.py  # Independent interval-arithmetic solution verifier
├── scripts/                    # Command-line utility scripts
│   ├── export_fixture_outcome.py # Exports tiny run outcome for frontend test mocking
│   └── run_small.py            # CLI tool to run algorithms A–D on sample instances
└── tests/                      # Full automated test suite (192 unit/integration tests)
```

---

## 🚀 Getting Started

### Prerequisites
* **Python:** 3.10 or higher (Python 3.14 fully supported).
* **Node.js:** 18 or higher (with `npm`).

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/MANANPATEL7310/UniSched-AI.git
   cd UniSched-AI
   ```

2. **Set up Python virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

---

## 💻 Running the Application

### Option A: Single-Command Production Demo (Recommended)
Build the frontend bundle once; FastAPI automatically serves the compiled SPA and REST API from a single port:

```bash
# 1. Build the production frontend bundle
npm --prefix frontend run build

# 2. Launch FastAPI server
uvicorn api.main:app --port 8000
```
Open **`http://localhost:8000`** in your browser.
* Interactive API documentation is available at **`http://localhost:8000/docs`**.

### Option B: Concurrent Development Mode
Run the backend with auto-reload and the Vite dev server with Hot Module Replacement (HMR):

* **Terminal 1 (Backend API):**
  ```bash
  uvicorn api.main:app --reload --port 8000
  ```
* **Terminal 2 (Frontend Vite Server):**
  ```bash
  cd frontend && npm run dev
  ```
Open **`http://localhost:5173`** (Vite proxies all `/api` requests to port 8000).

---

## 🧪 Testing and Verification

The repository contains a multi-tiered test suite verifying logic, API behavior, component accessibility, and architectural boundaries:

### 1. Backend Python Tests
```bash
# Run all 192 unit, engine, API, and architectural tests
pytest

# Run architectural boundary isolation tests
pytest tests/test_architecture.py

# Run solver cross-check on all sample instances
python3 scripts/run_small.py --sample all --algorithm D
```

### 2. Frontend React Tests
```bash
# Run all 85 component, reducer, layout, and a11y tests
npm --prefix frontend test -- --run
```

### 3. Production Build Validation
```bash
# Ensure strict TypeScript typing and production bundling
npm --prefix frontend run build
```

---

## 📊 Benchmark Datasets

The repository includes six hand-crafted named instances in `data/sample_data/` covering distinct scheduling scenarios:

1. **`tiny`:** 5 sessions, 2 days $\times$ 3 slots, 3 rooms. Hand-calculated solution used for base contract verification.
2. **`feasible_obvious`:** 2 sessions, loose constraints. Tests basic solver progress.
3. **`impossible`:** 2 sessions competing for 1 resource with 0 alternative slots. Tests immediate infeasibility proofs (Config D proves UNSAT with 0 nodes).
4. **`tight`:** 6 sessions, packed schedule with near-full utilization.
5. **`multihour_lab`:** Consecutive multi-slot lab sessions testing contiguous slot allocation without day-boundary overflow.
6. **`unavailability`:** Sessions with complex teacher and room blackout windows.

---

## 🔒 Architectural Rules

* **Isolation of CSP Engine:** `csp/` imports **only** standard Python libraries and `models/`. It never imports `pandas`, `fastapi`, `pydantic`, or external solvers.
* **Independent Validation:** `scheduling/timetable_validator.py` shares zero code with `csp/`. Solutions must pass interval arithmetic verification independently.
* **Deterministic Execution:** Given identical instances and configs, searches execute deterministically with strictly defined tie-breakers: `(fewest legal values → highest degree → smallest session_id)`.
* **Honest Limit Reporting:** Timeouts and node limits return `TIMEOUT` or `NODE_LIMIT`, never misreporting incompleteness as `INFEASIBLE_PROVEN`.

---

## 📜 License
Developed as part of the Foundations of Artificial Intelligence (FAI) curriculum.

