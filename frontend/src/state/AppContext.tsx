import {
  createContext,
  useContext,
  useEffect,
  useReducer,
  useRef,
  type Dispatch,
  type ReactNode,
} from "react";
import {
  appReducer,
  canGenerate,
  createInitialState,
  type Action,
  type AppState,
} from "./reducer.js";
import { saveDraftToStorage } from "./storage.js";
import { getSample, validateDraft } from "../api/client.js";
import type { InstanceDraft, RunOutcome } from "../api/types.js";
import sampleOutcome from "../tests/fixtures/tiny_outcome.json";
import bundledSample from "../data/tiny-sample.json";

export interface AppContextValue {
  state: AppState;
  dispatch: Dispatch<Action>;
  canGenerate: boolean;
}

export const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, undefined, createInitialState);
  const debounceTimerRef = useRef<number | undefined>(undefined);

  // Open with a real, labelled example so the first screen is useful immediately.
  useEffect(() => {
    let active = true;
    const boot = async () => {
      if (!state.draft) {
        dispatch({ type: "RUN_FINISHED", outcome: sampleOutcome as RunOutcome, error: null });
      }
      try {
        const draft = state.draft ?? await getSample("tiny");
        if (!active) return;
        if (!state.draft) dispatch({ type: "SET_DRAFT", draft, source: "Sample: tiny · 5 sessions" });
        const validation = await validateDraft(draft);
        if (active && validation.summary && !validation.parse_error) {
          dispatch({ type: "APPLY", applied: { draft, summary: validation.summary, issues: validation.issues } });
          if (!state.draft) dispatch({ type: "RUN_FINISHED", outcome: sampleOutcome as RunOutcome, error: null });
        }
      } catch {
        // The bundled, hand-verified sample keeps the prototype useful offline.
        if (!active) return;
        const draft = state.draft ?? bundledSample as InstanceDraft;
        if (!state.draft) dispatch({ type: "SET_DRAFT", draft, source: "Bundled sample: tiny · 5 sessions" });
        dispatch({ type: "APPLY", applied: { draft, summary: { courses: draft.courses.length, teachers: draft.teachers.length, rooms: draft.rooms.length, divisions: draft.divisions.length, sessions: 5 }, issues: [] } });
        if (!state.draft) dispatch({ type: "RUN_FINISHED", outcome: sampleOutcome as RunOutcome, error: null });
      }
    };
    void boot();
    return () => { active = false; };
  // Run once for the initial persisted draft state.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Debounced save to localStorage (500 ms)
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = window.setTimeout(() => {
        saveDraftToStorage(state.draft, state.sourceLabel);
      }, 500);
    }
    return () => {
      if (typeof window !== "undefined") {
        window.clearTimeout(debounceTimerRef.current);
      }
    };
  }, [state.draft, state.sourceLabel]);

  const value: AppContextValue = {
    state,
    dispatch,
    canGenerate: canGenerate(state),
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return ctx;
}

export const useAppContext = useApp;
