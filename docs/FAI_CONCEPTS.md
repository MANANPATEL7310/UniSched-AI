# Foundations of Artificial Intelligence (FAI) — Theoretical Mapping & Concepts

This document provides a formal theoretical analysis of the **University Course Timetabling System** through the lens of classical Artificial Intelligence and Constraint Satisfaction Problems (CSP).

---

## 1. The Intelligent Agent Model

In classical AI (Russell & Norvig, *Artificial Intelligence: A Modern Approach*), an **agent** is an entity that perceives its environment through sensors and acts upon that environment through actuators to achieve specified goals.

```
       +-------------------------------------------------------+
       |                  TIMETABLE SOLVER AGENT               |
       |                                                       |
       |   +---------------+      +------------------------+   |
       |   |    SENSORS    |      |       ACTUATORS        |   |
       |   | Input Data:   |      | Output Schedules:      |   |
       |   | - Days/Slots  |      | - Timetable Solution   |   |
       |   | - Teachers    | ---> | - CSV Export           |   |
       |   | - Courses     |      | - Validation Reports   |   |
       |   | - Rooms       |      | - Metrics & Traces     |   |
       |   | - Divisions   |      |                        |   |
       |   +---------------+      +------------------------+   |
       |           |                          ^                |
       |           v                          |                |
       |   +-----------------------------------------------+   |
       |   |            CLASSICAL CSP SEARCH CORE          |   |
       |   |   Backtracking + MRV/Degree/LCV + FC + MAC    |   |
       |   +-----------------------------------------------+   |
       +-------------------------------------------------------+
```

### Agent Architecture
* **Agent Type:** Goal-based, utility-informed problem-solving agent using systematic search.
* **Knowledge Representation:** Discrete constraint networks represented as variables, finite discrete domains, and explicit binary conflict relations.

---

## 2. PEAS Analysis

| PEAS Element | Description in Timetable CSP |
|---|---|
| **P**erformance Measure | 1. **Hard Constraint Satisfaction:** 100% adherence (0 hard violations required for validity).<br>2. **Computational Efficiency:** Minimized search node expansions, backtracks, and runtime.<br>3. **Soundness:** Immediate, proven determination of unsat (`INFEASIBLE_PROVEN`) when no schedule exists.<br>4. **Soft Metric Quality:** Minimized student gap hours, balanced teacher daily workload, satisfied teacher slot preferences. |
| **E**nvironment | Academic curriculum structure, faculty availability constraints, room capacities, room equipment types (`lecture`, `computer_lab`), student cohort course enrollments, and institutional weekly time grids. |
| **A**ctuators | Solution timetable generator, CSV table exporter, conflict validation reporter, search metric reporter, and execution cancel controller. |
| **S**ensors | Structured instance configuration files (CSV/JSON), programmatic REST API payloads, and interactive web table inputs. |

---

## 3. Environment Properties

Understanding the environment properties determines why classical systematic search is the optimal agent architecture:

1. **Fully Observable (vs. Partially Observable):**
   * *Property:* **Fully Observable.**
   * *Rationale:* The agent has complete, transparent access to all courses, teachers, rooms, cohorts, and constraints before search begins. There are no hidden variables or unobserved external states.

2. **Deterministic (vs. Stochastic):**
   * *Property:* **Deterministic.**
   * *Rationale:* The consequences of assigning a class session to $(\text{day}, \text{slot}, \text{room})$ are fully deterministic. Given identical inputs and search configurations, the algorithm yields identical execution paths and schedules every time.

3. **Static (vs. Dynamic):**
   * *Property:* **Static.**
   * *Rationale:* The problem instance does not mutate while the search algorithm is deliberating. Time limits and cancellations are monitored via polling, but the problem constraints remain stationary.

4. **Discrete (vs. Continuous):**
   * *Property:* **Discrete.**
   * *Rationale:* Time is quantized into distinct, numbered integer slots (e.g. 8 slots/day across 5 days); classrooms and faculty members are discrete categorical entities.

5. **Sequential (vs. Episodic):**
   * *Property:* **Sequential.**
   * *Rationale:* Variable assignments in depth-first search have cascading consequences. Assigning session $s_1$ to Room 101 at Mon@09:00 directly constrains which future states are reachable for all conflicting neighbor sessions.

6. **Single-Agent (vs. Multi-Agent):**
   * *Property:* **Single-Agent.**
   * *Rationale:* The solver operates as an autonomous monolithic deliberative engine. Other entities in the domain do not act strategically against the scheduler.

---

## 4. State-Space Formulation

* **Initial State:** Empty assignment set: $\alpha = \{\}$. All variables unassigned; all domains initialized to unary-filtered candidate values.
* **Actions / Transitions:** Assign an unassigned session $s_i$ an available consistent value $v \in D(s_i)$:
  $$\alpha' = \alpha \cup \{s_i \leftarrow v\}$$
* **Transition Model:** Deterministic state augmentation accompanied by trail checkpointing in `DomainState` to record reversible prunings.
* **Goal Test:** All $n$ sessions are assigned, and no binary constraint is violated:
  $$|\alpha| = n \quad \land \quad \forall (s_i, s_j), \, \text{keys}(s_i, \alpha[s_i]) \cap \text{keys}(s_j, \alpha[s_j]) = \emptyset$$
* **Path Cost:** In pure CSP satisfiability, all solution paths have uniform validity. For soft constraints, path cost is the total weighted penalty (student gaps, faculty overload).

---

## 5. Constraint Satisfaction Problem Formalization

A classical CSP is formally defined as a triple $(X, D, C)$:

### Variables ($X$)
$$X = \{s_1, s_2, \dots, s_n\}$$
Each variable corresponds to one required weekly class session, expanded from course frequencies:
$$s = \langle \text{course\_id}, \text{division\_id}, \text{teacher\_id}, \text{duration } k, \text{index } i \rangle$$

### Domains ($D$)
For each session $s$, its domain $D(s)$ consists of possible assignments $v = (d, t, r)$ where:
* $d \in \{0, \dots, D_{\text{days}} - 1\}$ (day index)
* $t \in \{0, \dots, S_{\text{slots}} - k\}$ (start slot index such that $t + k \le S_{\text{slots}}$)
* $r \in \text{Rooms}$

**Unary Filtering Rules (Enforced at Root):**
1. **Capacity:** $\text{capacity}(r) \ge \text{student\_count}(s.\text{division\_id})$.
2. **Room Type Compatibility:** $\text{type}(r) \in s.\text{room\_types}$.
3. **Teacher Availability:** For all $j \in [0, k-1]$, $(d, t + j) \notin \text{unavailable}(s.\text{teacher\_id})$.
4. **Room Availability:** For all $j \in [0, k-1]$, $(d, t + j) \notin \text{unavailable}(r)$.
5. **Day Overflow:** $t + k \le S_{\text{slots}}$ (strictly no multi-hour session crosses midnight).

### Binary Constraints ($C$) via Occupancy Keys
Any two distinct sessions $s_a \ne s_b$ cannot share the same physical resource at the same absolute slot.

For assignment $v = (d, t, r)$ of session $s$ with duration $k$, the **occupancy keys** are defined as:
$$\text{keys}(s, v) = \bigcup_{j=0}^{k-1} \left\{ (\text{"T"}, s.\text{teacher}, d \cdot S + t + j), \, (\text{"D"}, s.\text{division}, d \cdot S + t + j), \, (\text{"R"}, r, d \cdot S + t + j) \right\}$$

$$\text{Constraint } C(s_a, s_b): \quad \text{keys}(s_a, v_a) \cap \text{keys}(s_b, v_b) = \emptyset$$

---

## 6. Systematic Search & Pruning Strategies

```
             [Root: Empty Assignment]
                    /       \
              Try v1         Try v2
              /    \
         Assign s1  Backtrack (Restore DomainState)
          /      \
    [Propagation]
    - FC: prune neighbor domains
    - MAC: AC-3 queue on changed arcs
```

### 1. Config A: Baseline Backtracking
* Standard depth-first chronological search without heuristics.
* Variables ordered statically by sorted session ID; values ordered by domain index.
* Serves as experimental control group.

### 2. Config B: Variable & Value Ordering Heuristics
* **Minimum Remaining Values (MRV):** Picks unassigned variable $s$ with smallest legal domain $|D(s)|$. Fails first on difficult variables.
* **Degree Heuristic (Tie-Breaker):** Among MRV ties, picks the variable with the highest number of constraints on remaining unassigned variables.
* **Least Constraining Value (LCV):** Orders candidate values by counting how many values they eliminate from neighbor domains, attempting the most promising value first.

### 3. Config C: Forward Checking (FC)
* Whenever variable $X_i \leftarrow v$ is assigned, the algorithm looks ahead and removes all conflicting values from unassigned neighbors.
* **Domain Wipeout Detection:** If any neighbor's domain becomes empty ($|D(X_j)| = 0$), the branch immediately terminates and backtracks without wasting subtree expansions.

### 4. Config D: Root AC-3 + Maintaining Arc Consistency (MAC)
* **Root AC-3:** Before search begins, AC-3 evaluates all directional arcs $(X_i, X_j)$ between neighbor variables. Any value in $D(X_i)$ lacking support in $D(X_j)$ is permanently pruned.
* **MAC Search:** After assigning $X_i \leftarrow v$, Forward Checking prunes immediate neighbors, and any variable whose domain shrank places directional arcs onto the AC-3 queue to propagate transitive consequences.

---

## 7. Hand-Worked Example (Tracing Search Behavior)

### Problem Specification
* **Grid:** 1 Day, 2 Slots ($s_0, s_1$), 2 Rooms ($R_1, R_2$, capacity 50).
* **Faculty:** $T_1$ (teaches $X$ and $Y$), $T_2$ (teaches $Z$).
* **Divisions:** Division $A$ (30 students).
* **Sessions:** $X$ (by $T_1$), $Y$ (by $T_1$), $Z$ (by $T_2$), all duration 1 slot.
* **Unavailability:** $T_2$ is unavailable at slot $s_0$.

### Domains
* $D(X) = \{(0, R_1), (0, R_2), (1, R_1), (1, R_2)\}$ (4 candidate values)
* $D(Y) = \{(0, R_1), (0, R_2), (1, R_1), (1, R_2)\}$ (4 candidate values)
* $D(Z) = \{(1, R_1), (1, R_2)\}$ (2 candidate values, since $s_0$ is unavailable)

### Algorithm Execution Traces

1. **Config A (Chronological Backtracking):**
   * Chooses $X$ first (static order). Tries $X \leftarrow (0, R_1)$.
   * Chooses $Y$ next. Values $(0, R_1)$ and $(0, R_2)$ conflict with $X$ on teacher $T_1$ and division $A$. Tries $Y \leftarrow (1, R_1)$.
   * Chooses $Z$ next. Both $(1, R_1)$ and $(1, R_2)$ conflict with $Y$ on division $A$ at slot 1.
   * Backtracks to $Y$, tries $Y \leftarrow (1, R_2)$. Both $Z$ values still conflict on division $A$.
   * Backtracks to $X$, tries $X \leftarrow (0, R_2)$, repeats search.
   * **Result:** After exhausting all branches, concludes `INFEASIBLE_PROVEN` after multiple backtracks.

2. **Config B (Heuristics):**
   * MRV selects $Z$ first ($|D(Z)| = 2$ vs $4$). Assigns $Z \leftarrow (1, R_1)$.
   * MRV evaluates $X$ and $Y$; both have 2 legal values remaining at slot $s_0$. Selects $X$ (tie broken by session ID). Assigns $X \leftarrow (0, R_1)$.
   * $Y$ now has 0 legal values remaining (slot 0 taken by $T_1/A$, slot 1 taken by $A$).
   * MRV immediately selects $Y$, detects 0 candidates, and backtracks immediately.
   * **Result:** Proves infeasibility with substantially fewer node expansions than Config A.

3. **Config C (Forward Checking):**
   * MRV picks $Z \leftarrow (1, R_1)$.
   * Forward checking immediately prunes all slot 1 values from $X$ and $Y$ (division $A$ conflict).
   * Remaining domains: $D(X) = \{(0, R_1), (0, R_2)\}$, $D(Y) = \{(0, R_1), (0, R_2)\}$.
   * Assigns $X \leftarrow (0, R_1)$.
   * Forward checking prunes all slot 0 values from $Y$ ($T_1$ and division $A$ conflict).
   * **Domain wipeout:** $|D(Y)| = 0$. Forward check returns `False` immediately.
   * **Result:** Search halts without exploring deeper assignments for $Y$.

4. **Config D (Root AC-3 + MAC):**
   * **Root AC-3 preprocessing begins before search:**
     * Evaluates arc $(X, Z)$: Every value of $X$ at slot 1 conflicts on division $A$ with all values of $Z$ (which are only at slot 1). Therefore, $(1, R_1)$ and $(1, R_2)$ have no support in $Z$ and are **pruned**. $D(X)$ becomes $\{(0, R_1), (0, R_2)\}$.
     * Evaluates arc $(Y, Z)$: Similarly, slot 1 values of $Y$ have no support in $Z$ and are **pruned**. $D(Y)$ becomes $\{(0, R_1), (0, R_2)\}$.
     * Removals re-queue arc $(Y, X)$: Now, every remaining value in $D(Y)$ (at slot 0) clashes with every remaining value in $D(X)$ on teacher $T_1$ and division $A$. Neither slot 0 value in $Y$ has support in $X$. Both are **pruned**.
     * **Domain wipeout:** $D(Y) = \emptyset$.
   * **Result:** Root AC-3 proves `INFEASIBLE_PROVEN` with **0 search nodes** before search ever starts.

---

## 8. Why Machine Learning is Inappropriate for Hard CSP Timetabling

| Dimension | Machine Learning / Neural Approximations | Classical CSP Symbolic AI (UniSched-AI) |
|---|---|---|
| **Constraint Violation** | Probabilistic; statistical tendency to hallucinate near-valid schedules with subtle overlaps. | **Zero tolerance.** Solutions are certified 100% violation-free by independent interval validator. |
| **Infeasibility Proof** | Incapable of mathematically proving unsat; outputs low-confidence invalid schedules. | **Exact soundness.** Exhaustive search and AC-3 wipeout mathematically prove when no valid timetable exists. |
| **Determinism** | Sensitive to weights, seeds, temperature, and floating-point stochasticity. | **Strictly deterministic.** Same input + config always produces the exact same schedule. |
| **Explainability** | Black-box weights and opaque embeddings. | Transparent variable selections, domain pruning counts, and constraint explanations. |
| **Data Requirements** | Requires thousands of historic training schedules. | **Zero training data required.** Operates purely from first principles on institutional constraint specifications. |
