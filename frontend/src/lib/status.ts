import type { AppState } from "../state/reducer.js";
import { hasErrors } from "../state/reducer.js";

export type StatusCode =
  | "NO_DATA"
  | "UNAPPLIED"
  | "INPUT_ERRORS"
  | "READY"
  | "RUNNING"
  | "VALID"
  | "INVALID"
  | "INFEASIBLE"
  | "TIMEOUT"
  | "NODE_LIMIT"
  | "CANCELLED"
  | "ERROR";

export type StatusTone = "grey" | "blue" | "green" | "red" | "orange" | "yellow";

export interface StatusInfo {
  code: StatusCode;
  tone: StatusTone;
  text: string;
}

export function deriveStatus(s: AppState, running: boolean): StatusInfo {
  // 1. NO_DATA: draft == null
  if (s.draft === null) {
    return {
      code: "NO_DATA",
      tone: "grey",
      text: "No data loaded.",
    };
  }

  // 2. UNAPPLIED: dirty or applied == null
  if (s.dirty || s.applied === null) {
    return {
      code: "UNAPPLIED",
      tone: "yellow",
      text: "Changes not validated yet. Press Validate & Apply.",
    };
  }

  // 3. INPUT_ERRORS: any ERROR in applied.issues
  if (hasErrors(s.applied.issues)) {
    const errorCount = s.applied.issues.filter((i) => i.severity === "ERROR").length;
    return {
      code: "INPUT_ERRORS",
      tone: "red",
      text: `Input has ${errorCount} error(s). Fix them in Data Management.`,
    };
  }

  // 4. RUNNING: running
  if (running) {
    return {
      code: "RUNNING",
      tone: "blue",
      text: "Search in progress…",
    };
  }

  // 5. ERROR: runError != null
  if (s.runError !== null) {
    return {
      code: "ERROR",
      tone: "red",
      text: `Unexpected error: ${s.runError.message}`,
    };
  }

  // 6. READY: outcome == null
  if (s.outcome === null) {
    return {
      code: "READY",
      tone: "blue",
      text: "Ready to generate.",
    };
  }

  // 7. VALID: outcome.is_valid
  if (s.outcome.is_valid) {
    return {
      code: "VALID",
      tone: "green",
      text: `Valid timetable: 0 hard-constraint violations, all ${s.outcome.num_sessions} sessions scheduled.`,
    };
  }

  // 8. INVALID: status SOLVED and not valid
  if (s.outcome.status === "SOLVED" && !s.outcome.is_valid) {
    const vCount = s.outcome.validation?.violations.length ?? 0;
    return {
      code: "INVALID",
      tone: "red",
      text: `The solver returned a timetable but the independent validator found ${vCount} violation(s). Do not use it.`,
    };
  }

  // 9. INFEASIBLE: INFEASIBLE_PROVEN
  if (s.outcome.status === "INFEASIBLE_PROVEN") {
    const msg = s.outcome.message ? ` ${s.outcome.message}` : "";
    return {
      code: "INFEASIBLE",
      tone: "orange",
      text: `No valid timetable exists under the modelled constraints (the search finished completely).${msg}`,
    };
  }

  // 10. TIMEOUT: TIMEOUT
  if (s.outcome.status === "TIMEOUT") {
    const runtime = s.outcome.metrics?.runtime_s ?? 0;
    return {
      code: "TIMEOUT",
      tone: "yellow",
      text: `Time limit reached after ${runtime} s. This does NOT prove the problem is infeasible. Try a longer limit or algorithm C or D.`,
    };
  }

  // 11. NODE_LIMIT: NODE_LIMIT
  if (s.outcome.status === "NODE_LIMIT") {
    return {
      code: "NODE_LIMIT",
      tone: "yellow",
      text: "Node limit reached. This does NOT prove infeasibility.",
    };
  }

  // 12. CANCELLED: CANCELLED
  if (s.outcome.status === "CANCELLED") {
    return {
      code: "CANCELLED",
      tone: "grey",
      text: "Search cancelled.",
    };
  }

  return {
    code: "READY",
    tone: "grey",
    text: s.outcome.message || s.outcome.status,
  };
}
