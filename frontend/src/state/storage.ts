import type { InstanceDraft } from "../api/types.js";

export const STORAGE_KEY = "timetable.draft.v1";

export interface StoredDraftData {
  draft: InstanceDraft;
  sourceLabel: string;
}

export function loadDraftFromStorage(): StoredDraftData | null {
  try {
    if (typeof window === "undefined" || !window.localStorage) {
      return null;
    }
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (
      parsed &&
      typeof parsed === "object" &&
      parsed.draft &&
      typeof parsed.sourceLabel === "string"
    ) {
      return {
        draft: parsed.draft as InstanceDraft,
        sourceLabel: parsed.sourceLabel,
      };
    }
  } catch {
    // Corrupt or inaccessible localStorage is safely ignored
  }
  return null;
}

export function saveDraftToStorage(
  draft: InstanceDraft | null,
  sourceLabel: string
): void {
  try {
    if (typeof window === "undefined" || !window.localStorage) {
      return;
    }
    if (!draft) {
      window.localStorage.removeItem(STORAGE_KEY);
      return;
    }
    const data: StoredDraftData = { draft, sourceLabel };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // Storage quota errors or privacy mode blockages ignored
  }
}

export function clearDraftStorage(): void {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // ignore
  }
}
