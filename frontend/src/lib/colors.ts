/**
 * Deterministic color assignment for courses.
 * Uses a fixed hash based on course ID position in the sorted course list.
 */

export interface CourseColorStyle {
  hue: number;
  backgroundColor: string;
  borderColor: string;
  textColor: string;
}

export function courseColor(
  courseId: string,
  allCourseIds: string[]
): CourseColorStyle {
  const sorted = Array.from(new Set(allCourseIds)).sort();
  const index = sorted.indexOf(courseId);
  const safeIndex = index >= 0 ? index : 0;
  const hue = (safeIndex * 47) % 360;

  return {
    hue,
    backgroundColor: `hsl(${hue} 65% var(--card-l, 88%))`,
    borderColor: `hsl(${hue} 60% 45%)`,
    textColor: `var(--card-text, hsl(${hue} 80% 20%))`,
  };
}
