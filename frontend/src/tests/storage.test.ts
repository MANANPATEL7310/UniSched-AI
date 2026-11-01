import { beforeEach, describe, expect, it } from "vitest";
import {
  clearDraftStorage,
  loadDraftFromStorage,
  saveDraftToStorage,
  STORAGE_KEY,
} from "../state/storage.js";
import type { InstanceDraft } from "../api/types.js";

const mockDraft: InstanceDraft = {
  name: "saved_instance",
  days: ["Mon", "Tue"],
  slots: [{ start: "09:00", end: "10:00" }],
  teachers: [],
  courses: [],
  divisions: [],
  rooms: [],
  fixed_assignments: [],
};

describe("storage helpers", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("saves and loads draft data to/from localStorage", () => {
    expect(loadDraftFromStorage()).toBeNull();
    saveDraftToStorage(mockDraft, "Sample: saved");

    const loaded = loadDraftFromStorage();
    expect(loaded).not.toBeNull();
    expect(loaded?.sourceLabel).toBe("Sample: saved");
    expect(loaded?.draft.name).toBe("saved_instance");
  });

  it("clears storage when draft is null or clearDraftStorage called", () => {
    saveDraftToStorage(mockDraft, "Sample: saved");
    expect(loadDraftFromStorage()).not.toBeNull();

    clearDraftStorage();
    expect(loadDraftFromStorage()).toBeNull();
  });

  it("safely ignores corrupt JSON in localStorage without throwing", () => {
    localStorage.setItem(STORAGE_KEY, "INVALID_JSON_{{[[");
    expect(() => {
      const res = loadDraftFromStorage();
      expect(res).toBeNull();
    }).not.toThrow();
  });
});
