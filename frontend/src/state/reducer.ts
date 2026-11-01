import type {
  Algorithm,
  ApiErrorBody,
  BenchmarkRow,
  InputIssue,
  InstanceDraft,
  InstanceSummary,
  RunOutcome,
} from "../api/types.js";
import { loadDraftFromStorage } from "./storage.js";

export interface AppliedState {
  draft: InstanceDraft;
  summary: InstanceSummary;
  issues: InputIssue[];
}

export interface AppState {
  draft: InstanceDraft | null;
  applied: AppliedState | null;
  dirty: boolean;
  sourceLabel: string;
  runId: string | null;
  runAlgorithm: Algorithm | null;
  outcome: RunOutcome | null;
  runError: ApiErrorBody | null;
  benchRows: BenchmarkRow[] | null;
  benchMeta: Record<string, unknown> | null;
}

export type Action =
  | { type: "SET_DRAFT"; draft: InstanceDraft; source: string }
  | { type: "EDIT_DRAFT"; draft: InstanceDraft }
  | { type: "APPLY"; applied: AppliedState }
  | { type: "RUN_STARTED"; runId: string; algorithm: Algorithm }
  | { type: "RUN_FINISHED"; outcome: RunOutcome | null; error: ApiErrorBody | null }
  | { type: "RESET_RESULTS" }
  | { type: "SET_BENCH"; rows: BenchmarkRow[]; meta: Record<string, unknown> | null };

export function hasErrors(issues: InputIssue[]): boolean {
  return issues.some((i) => i.severity === "ERROR");
}

export function canGenerate(state: AppState): boolean {
  return state.applied !== null && !hasErrors(state.applied.issues) && !state.dirty;
}

export function createInitialState(): AppState {
  const stored = loadDraftFromStorage();
  return {
    draft: stored ? stored.draft : null,
    applied: null,
    dirty: stored ? true : false,
    sourceLabel: stored ? stored.sourceLabel : "None",
    runId: null,
    runAlgorithm: null,
    outcome: null,
    runError: null,
    benchRows: null,
    benchMeta: null,
  };
}

export function appReducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "SET_DRAFT":
      return {
        ...state,
        draft: action.draft,
        sourceLabel: action.source,
        applied: null,
        dirty: false,
        // Reset rule: never show timetable that belongs to older data
        runId: null,
        runAlgorithm: null,
        outcome: null,
        runError: null,
      };

    case "EDIT_DRAFT":
      return {
        ...state,
        draft: action.draft,
        dirty: true,
      };

    case "APPLY":
      return {
        ...state,
        applied: action.applied,
        draft: action.applied ? action.applied.draft : state.draft,
        dirty: false,
        // Reset rule: applying new data clears results
        runId: null,
        runAlgorithm: null,
        outcome: null,
        runError: null,
      };

    case "RUN_STARTED":
      return {
        ...state,
        runId: action.runId,
        runAlgorithm: action.algorithm,
        runError: null,
      };

    case "RUN_FINISHED":
      return {
        ...state,
        outcome: action.outcome,
        runError: action.error,
      };

    case "RESET_RESULTS":
      return {
        ...state,
        runId: null,
        runAlgorithm: null,
        outcome: null,
        runError: null,
      };

    case "SET_BENCH":
      return {
        ...state,
        benchRows: action.rows,
        benchMeta: action.meta,
      };

    default:
      return state;
  }
}
