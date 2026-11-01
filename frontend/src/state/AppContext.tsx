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

export interface AppContextValue {
  state: AppState;
  dispatch: Dispatch<Action>;
  canGenerate: boolean;
}

export const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, undefined, createInitialState);
  const debounceTimerRef = useRef<number | undefined>(undefined);

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
