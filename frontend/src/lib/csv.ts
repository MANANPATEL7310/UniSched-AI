import type { Entry } from "../api/types.js";

/**
 * Escapes a single CSV field per RFC 4180:
 * Encloses the field in double quotes if it contains commas, double quotes, or newlines.
 * Internal double quotes are escaped by doubling them ("").
 */
export function escapeCsvField(val: string | number | null | undefined): string {
  if (val === null || val === undefined) return "";
  const str = String(val);
  if (str.includes(",") || str.includes('"') || str.includes("\n") || str.includes("\r")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

/**
 * Converts a list of timetable Entry objects into RFC 4180 CSV text.
 * Header: Day,Start,End,Duration (slots),Course,Teacher,Division,Room,Session ID
 * Line separator: \r\n
 */
export function entriesToCsv(entries: Entry[]): string {
  const header = "Day,Start,End,Duration (slots),Course,Teacher,Division,Room,Session ID";
  const rows = entries.map((e) => {
    return [
      escapeCsvField(e.day_name),
      escapeCsvField(e.start_time),
      escapeCsvField(e.end_time),
      escapeCsvField(e.duration_slots),
      escapeCsvField(e.course_name),
      escapeCsvField(e.teacher_name),
      escapeCsvField(e.division_name),
      escapeCsvField(e.room_name),
      escapeCsvField(e.session_id),
    ].join(",");
  });

  return [header, ...rows].join("\r\n");
}

/**
 * Triggers a browser download of CSV content with a UTF-8 BOM (\uFEFF)
 * for Excel compatibility.
 */
export function downloadCsvBlob(content: string, filename: string): void {
  const bom = "\uFEFF";
  const blob = new Blob([bom + content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
