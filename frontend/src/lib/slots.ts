/**
 * Helpers for slot string representations, e.g. "Mon@09:00".
 */

export function slotKey(day: string, startTime: string): string {
  return `${day}@${startTime}`;
}

export function parseSlotKey(
  key: string
): { day: string; startTime: string } | null {
  const parts = key.split("@");
  if (parts.length !== 2) return null;
  const day = parts[0]?.trim();
  const startTime = parts[1]?.trim();
  if (!day || !startTime) return null;
  return { day, startTime };
}

export function formatTimeRange(start: string, end: string): string {
  return `${start}–${end}`;
}

export function compareTimes(t1: string, t2: string): number {
  return t1.localeCompare(t2);
}
