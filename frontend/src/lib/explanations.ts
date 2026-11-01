import type { Algorithm, RunOutcome } from "../api/types";

export interface AlgorithmInfo {
  code: Algorithm;
  name: string;
  tagline: string;
  description: string;
  badge: string;
}

export const ALGORITHM_OPTIONS: AlgorithmInfo[] = [
  {
    code: "A",
    name: "Config A: Baseline Backtracking",
    tagline: "Pure backtracking with static order",
    description: "A simple starting point. Places sessions in order and backtracks when a choice blocks the rest.",
    badge: "Baseline",
  },
  {
    code: "B",
    name: "Config B: MRV + Degree + LCV",
    tagline: "Dynamic variable and value ordering heuristics",
    description: "Uses smart ordering to schedule the hardest-to-place class first, then preserves the most options for others.",
    badge: "Heuristics",
  },
  {
    code: "C",
    name: "Config C: Forward Checking",
    tagline: "Lookahead filtering on neighbors",
    description: "After each placement, checks nearby classes for conflicts and abandons dead ends early.",
    badge: "Propagation",
  },
  {
    code: "D",
    name: "Config D: AC-3 + MAC",
    tagline: "Full arc consistency before and during search",
    description: "Checks compatibility across related classes before and during the search. A strong choice for tighter schedules.",
    badge: "Full Inference",
  },
];

export function explainRun(outcome: RunOutcome): string[] {
  const sentences: string[] = [];
  const { metrics, algorithm, status, num_sessions } = outcome;

  // 1. General search workload statement (always present)
  sentences.push(
    `The scheduler had ${num_sessions} sessions to place. It tried ${metrics.attempts.toLocaleString()} candidate assignments and undid ${metrics.backtracks.toLocaleString()} of them.`
  );

  // 2. Algorithm specific heuristic details
  if (algorithm === "B" || algorithm === "C" || algorithm === "D") {
    sentences.push(
      "MRV always picked the session with the fewest legal options; ties were broken by Degree, then by session id."
    );
  }

  // 3. Forward checking details
  if (algorithm === "C") {
    sentences.push(
      `Forward checking removed ${metrics.values_pruned.toLocaleString()} values from other sessions' options and hit a dead end ${metrics.domain_wipeouts.toLocaleString()} times, stopping bad branches early.`
    );
  }

  // 4. Arc consistency (AC-3 / MAC) details
  if (algorithm === "D") {
    sentences.push(
      `AC-3 removed ${metrics.root_pruned.toLocaleString()} values before the search began. MAC kept pairs of sessions consistent after every assignment.`
    );
  }

  // 5. Outcome status interpretation
  switch (status) {
    case "SOLVED":
      sentences.push(
        `Search successfully found a complete, conflict-free timetable satisfying all hard constraints in ${metrics.runtime_s.toFixed(3)} s (${metrics.nodes.toLocaleString()} search nodes).`
      );
      break;
    case "INFEASIBLE_PROVEN":
      sentences.push(
        `No valid timetable exists under the modelled constraints (the search finished completely). ${outcome.message || ""}`
      );
      break;
    case "TIMEOUT":
      sentences.push(
        `Time limit reached after ${metrics.runtime_s.toFixed(1)} s. This does NOT prove the problem is infeasible. Try a longer limit or algorithm C or D.`
      );
      break;
    case "NODE_LIMIT":
      sentences.push(
        `Node limit reached (${metrics.nodes.toLocaleString()} nodes). This does NOT prove infeasibility.`
      );
      break;
    case "CANCELLED":
      sentences.push("Search cancelled by user request.");
      break;
  }

  return sentences;
}

