export type RoomType = "lecture" | "computer_lab" | "general_lab";
export type Algorithm = "A" | "B" | "C" | "D";
export type SearchStatus = "SOLVED" | "INFEASIBLE_PROVEN" | "TIMEOUT" | "NODE_LIMIT" | "CANCELLED";
export type RunState = "running" | "done" | "error";

export interface SlotDef {
  start: string;
  end: string;
}

export interface TeacherRow {
  teacher_id: string;
  teacher_name: string;
  unavailable_slots: string[];
  preferred_slots: string[];
  max_daily_sessions: number | null;
}

export interface CourseRow {
  course_id: string;
  course_name: string;
  teacher_id: string;
  sessions_per_week: number;
  duration_slots: number;
  room_types: RoomType[];
  eligible_divisions: string[];
}

export interface DivisionRow {
  division_id: string;
  division_name: string;
  student_count: number;
  enrolled_courses: string[];
}

export interface RoomRow {
  room_id: string;
  room_name: string;
  room_type: RoomType;
  capacity: number;
  unavailable_slots: string[];
}

export interface FixedRow {
  session_id: string;
  day_name: string;
  start_time: string;
  room_id: string;
}

/** The editable form of an instance. Slot strings look like "Mon@09:00". */
export interface InstanceDraft {
  name: string;
  days: string[];
  slots: SlotDef[];
  teachers: TeacherRow[];
  courses: CourseRow[];
  divisions: DivisionRow[];
  rooms: RoomRow[];
  fixed_assignments: FixedRow[];
}

export interface InputIssue {
  severity: "ERROR" | "WARNING";
  code: string;
  message: string;
  entity: string | null;
}

export interface InstanceSummary {
  courses: number;
  teachers: number;
  rooms: number;
  divisions: number;
  sessions: number;
}

export interface ValidateResponse {
  parse_error: string | null;
  issues: InputIssue[];
  summary: InstanceSummary | null;
}

export interface GeneratorConfigDto {
  name: string;
  num_days: number;
  slots_per_day: number;
  num_divisions: number;
  num_teachers: number;
  num_courses: number;
  num_rooms: number;
  availability_density: number;
  tightness: number;
  seed: number;
}

export interface RunConfigDto {
  algorithm: Algorithm;
  timeout_s: number;
  node_limit: number | null;
}

export interface Progress {
  total: number;
  assigned: number;
  nodes: number;
  attempts: number;
  backtracks: number;
  elapsed_s: number;
}

export interface Metrics {
  nodes: number;
  attempts: number;
  backtracks: number;
  checks: number;
  values_pruned: number;
  root_pruned: number;
  domain_wipeouts: number;
  runtime_s: number;
  build_s: number;
  peak_memory_kb: number | null;
}

export interface Entry {
  session_id: string;
  course_id: string;
  course_name: string;
  teacher_id: string;
  teacher_name: string;
  division_id: string;
  division_name: string;
  room_id: string;
  room_name: string;
  day: number;
  day_name: string;
  start_slot: number;
  end_slot: number;
  start_time: string;
  end_time: string;
  duration_slots: number;
}

export interface GridDto {
  day_names: string[];
  slot_starts: string[];
  slot_ends: string[];
}

export interface TimetableDto {
  grid: GridDto;
  entries: Entry[];
}

export type ViolationType =
  | "MISSING_SESSION"
  | "DUPLICATE_SESSION"
  | "UNKNOWN_SESSION"
  | "TEACHER_CONFLICT"
  | "DIVISION_CONFLICT"
  | "ROOM_CONFLICT"
  | "CAPACITY"
  | "ROOM_TYPE"
  | "TEACHER_UNAVAILABLE"
  | "ROOM_UNAVAILABLE"
  | "DURATION"
  | "OUT_OF_RANGE"
  | "UNKNOWN_ROOM"
  | "FIXED_ASSIGNMENT";

export interface Violation {
  type: ViolationType;
  session_ids: string[];
  resource: string | null;
  day: number | null;
  slot: number | null;
  explanation: string;
}

export interface ValidationDto {
  is_valid: boolean;
  sessions_required: number;
  sessions_assigned: number;
  counts_by_type: Record<ViolationType, number>;
  violations: Violation[];
}

export interface SoftDto {
  student_gap: number;
  teacher_gap: number;
  workload: number;
  preference: number;
  change: number;
  total: number;
}

export interface RunOutcome {
  run_id: string;
  algorithm: Algorithm;
  status: SearchStatus;
  message: string;
  is_valid: boolean;
  num_sessions: number;
  metrics: Metrics;
  timetable: TimetableDto | null;
  validation: ValidationDto | null;
  soft: SoftDto | null;
}

export interface RunResponse {
  run_id: string;
  state: RunState;
  progress: Progress;
  outcome: RunOutcome | null;
  error: ApiErrorBody | null;
}

export interface BenchmarkRequest {
  sizes: ("small" | "medium" | "large")[];
  algorithms: Algorithm[];
  seeds: number;
  timeout_s: number;
  measure_memory: boolean;
}

export interface BenchmarkRow {
  instance: string;
  size_label: string;
  num_sessions: number;
  seed: number;
  algorithm: Algorithm;
  status: SearchStatus;
  solved: boolean;
  valid: boolean;
  runtime_s: number;
  build_s: number;
  nodes: number;
  attempts: number;
  backtracks: number;
  checks: number;
  values_pruned: number;
  peak_memory_kb: number | null;
  hard_violations: number;
  soft_penalty: number | null;
  timeout_s: number;
}

export interface BenchmarkResponse {
  job_id: string;
  state: RunState;
  done: number;
  total: number;
  rows: BenchmarkRow[] | null;
  meta: Record<string, unknown> | null;
  error: ApiErrorBody | null;
}

export interface SavedResultInfo {
  name: string;
  created: string;
  rows: number;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}

export interface SampleInfo {
  name: string;
  description: string;
}
