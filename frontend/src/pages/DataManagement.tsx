import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import { useApp } from "../state/AppContext.js";
import {
  generateInstance,
  getPresets,
  getSample,
  listSamples,
  uploadCsv,
  validateDraft,
} from "../api/client.js";
import type {
  CourseRow,
  DivisionRow,
  FixedRow,
  GeneratorConfigDto,
  InstanceDraft,
  RoomRow,
  RoomType,
  SampleInfo,
  SlotDef,
  TeacherRow,
} from "../api/types.js";
import { EditableTable, type Column } from "../components/EditableTable.js";
import { IssuesTable } from "../components/IssuesTable.js";

type SourceTab = "sample" | "upload" | "generate";
type EditorTab =
  | "days_slots"
  | "teachers"
  | "courses"
  | "divisions"
  | "rooms"
  | "fixed";

const CSV_REQUIRED_NAMES = [
  "days.csv",
  "slots.csv",
  "teachers.csv",
  "courses.csv",
  "divisions.csv",
  "rooms.csv",
];
const CSV_OPTIONAL_NAMES = ["fixed_assignments.csv"];

const ROOM_TYPE_OPTIONS: { value: RoomType; label: string }[] = [
  { value: "lecture", label: "Lecture" },
  { value: "computer_lab", label: "Computer Lab" },
  { value: "general_lab", label: "General Lab" },
];

export function DataManagement() {
  const { state, dispatch } = useApp();
  const draft = state.draft;

  // Source Panel state
  const [sourceTab, setSourceTab] = useState<SourceTab>("sample");
  const [samples, setSamples] = useState<SampleInfo[]>([]);
  const [selectedSample, setSelectedSample] = useState<string>("");
  const [loadingSample, setLoadingSample] = useState(false);

  // Upload CSV state
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Generate state
  const [presets, setPresets] = useState<Record<string, GeneratorConfigDto>>({});
  const [selectedPresetName, setSelectedPresetName] = useState<string>("small");
  const [genSeed, setGenSeed] = useState<number>(1);
  const [generating, setGenerating] = useState(false);
  const [showAdvancedGen, setShowAdvancedGen] = useState(false);
  const [customGenConfig, setCustomGenConfig] = useState<GeneratorConfigDto>({
    name: "custom",
    num_days: 5,
    slots_per_day: 6,
    num_divisions: 2,
    num_teachers: 6,
    num_courses: 8,
    num_rooms: 4,
    availability_density: 0.8,
    tightness: 0.6,
    seed: 1,
  });

  // Editor tab state
  const [editorTab, setEditorTab] = useState<EditorTab>("days_slots");
  const [validating, setValidating] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);

  // Fetch samples and presets on mount
  useEffect(() => {
    let mounted = true;
    listSamples()
      .then((data) => {
        if (mounted && data.length > 0) {
          setSamples(data);
          setSelectedSample(data[0]?.name || "");
        }
      })
      .catch(() => {});

    getPresets()
      .then((data) => {
        if (mounted && Object.keys(data).length > 0) {
          setPresets(data);
        }
      })
      .catch(() => {});

    return () => {
      mounted = false;
    };
  }, []);

  // --- Handlers for Source Panel ---

  const handleLoadSample = async () => {
    if (!selectedSample) return;
    setLoadingSample(true);
    setParseError(null);
    try {
      const loaded = await getSample(selectedSample);
      dispatch({
        type: "SET_DRAFT",
        draft: loaded,
        source: `Sample: ${selectedSample}`,
      });
    } catch (err: any) {
      setParseError(err.message || "Failed to load sample");
    } finally {
      setLoadingSample(false);
    }
  };

  const handleFilesSelected = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files));
      setUploadError(null);
    }
  };

  const handleUploadCsv = async () => {
    if (selectedFiles.length === 0) return;
    setUploading(true);
    setUploadError(null);
    setParseError(null);
    try {
      const loaded = await uploadCsv(selectedFiles);
      dispatch({
        type: "SET_DRAFT",
        draft: loaded,
        source: "Uploaded CSV",
      });
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload and parse CSVs");
    } finally {
      setUploading(false);
    }
  };

  const handleGenerateInstance = async () => {
    setGenerating(true);
    setParseError(null);
    try {
      const baseCfg = presets[selectedPresetName] || customGenConfig;
      const cfg: GeneratorConfigDto = {
        ...baseCfg,
        seed: genSeed,
        ...(showAdvancedGen ? customGenConfig : {}),
      };
      const loaded = await generateInstance(cfg);
      dispatch({
        type: "SET_DRAFT",
        draft: loaded,
        source: `Generated: ${cfg.name || selectedPresetName} (seed ${cfg.seed})`,
      });
    } catch (err: any) {
      setParseError(err.message || "Failed to generate instance");
    } finally {
      setGenerating(false);
    }
  };

  // --- Editor Table Configurations ---

  const teacherOptions = useMemo(() => {
    return (
      draft?.teachers.map((t) => ({
        value: t.teacher_id,
        label: `${t.teacher_name} (${t.teacher_id})`,
      })) || []
    );
  }, [draft?.teachers]);

  const divisionOptions = useMemo(() => {
    return (
      draft?.divisions.map((d) => ({
        value: d.division_id,
        label: `${d.division_name} (${d.division_id})`,
      })) || []
    );
  }, [draft?.divisions]);

  const courseOptions = useMemo(() => {
    return (
      draft?.courses.map((c) => ({
        value: c.course_id,
        label: `${c.course_name} (${c.course_id})`,
      })) || []
    );
  }, [draft?.courses]);

  const roomOptions = useMemo(() => {
    return (
      draft?.rooms.map((r) => ({
        value: r.room_id,
        label: `${r.room_name} (${r.room_id})`,
      })) || []
    );
  }, [draft?.rooms]);

  const dayOptions = useMemo(() => {
    return draft?.days.map((d) => ({ value: d, label: d })) || [];
  }, [draft?.days]);

  const slotOptions = useMemo(() => {
    return draft?.slots.map((s) => ({ value: s.start, label: s.start })) || [];
  }, [draft?.slots]);

  // Teachers columns
  const teacherColumns: Column<TeacherRow>[] = [
    { key: "teacher_id", header: "Teacher ID", kind: "text", required: true, isId: true },
    { key: "teacher_name", header: "Name", kind: "text", required: true },
    {
      key: "unavailable_slots",
      header: "Unavailable Slots",
      kind: "availability",
      availabilityModalTitle: (r) => `Unavailable Slots for ${r.teacher_name || r.teacher_id}`,
    },
    {
      key: "preferred_slots",
      header: "Preferred Slots",
      kind: "availability",
      availabilityModalTitle: (r) => `Preferred Slots for ${r.teacher_name || r.teacher_id}`,
    },
    { key: "max_daily_sessions", header: "Max Daily Sessions", kind: "int", min: 1, placeholder: "No limit" },
  ];

  // Courses columns
  const courseColumns: Column<CourseRow>[] = [
    { key: "course_id", header: "Course ID", kind: "text", required: true, isId: true },
    { key: "course_name", header: "Course Name", kind: "text", required: true },
    { key: "teacher_id", header: "Teacher", kind: "select", options: teacherOptions, required: true },
    { key: "sessions_per_week", header: "Sessions/Wk", kind: "int", min: 1, required: true },
    { key: "duration_slots", header: "Duration (slots)", kind: "int", min: 1, required: true },
    { key: "room_types", header: "Allowed Room Types", kind: "multiselect", options: ROOM_TYPE_OPTIONS },
    { key: "eligible_divisions", header: "Eligible Divisions", kind: "multiselect", options: divisionOptions },
  ];

  // Divisions columns
  const divisionColumns: Column<DivisionRow>[] = [
    { key: "division_id", header: "Division ID", kind: "text", required: true, isId: true },
    { key: "division_name", header: "Division Name", kind: "text", required: true },
    { key: "student_count", header: "Students", kind: "int", min: 1, required: true },
    { key: "enrolled_courses", header: "Enrolled Courses", kind: "multiselect", options: courseOptions },
  ];

  // Rooms columns
  const roomColumns: Column<RoomRow>[] = [
    { key: "room_id", header: "Room ID", kind: "text", required: true, isId: true },
    { key: "room_name", header: "Room Name", kind: "text", required: true },
    { key: "room_type", header: "Type", kind: "select", options: ROOM_TYPE_OPTIONS, required: true },
    { key: "capacity", header: "Capacity", kind: "int", min: 1, required: true },
    {
      key: "unavailable_slots",
      header: "Unavailable Slots",
      kind: "availability",
      availabilityModalTitle: (r) => `Unavailable Slots for ${r.room_name || r.room_id}`,
    },
  ];

  // Fixed assignments columns
  const fixedColumns: Column<FixedRow>[] = [
    { key: "session_id", header: "Session ID", kind: "text", required: true, placeholder: "e.g. FAI|A|1" },
    { key: "day_name", header: "Day", kind: "select", options: dayOptions, required: true },
    { key: "start_time", header: "Start Time", kind: "select", options: slotOptions, required: true },
    { key: "room_id", header: "Room", kind: "select", options: roomOptions, required: true },
  ];

  // --- Handlers for Validate & Apply ---

  const handleValidateAndApply = async () => {
    if (!draft) return;
    setValidating(true);
    setParseError(null);
    try {
      const res = await validateDraft(draft);
      if (res.parse_error) {
        setParseError(res.parse_error);
      } else {
        dispatch({
          type: "APPLY",
          applied: {
            draft: structuredClone(draft),
            summary: res.summary!,
            issues: res.issues,
          },
        });
      }
    } catch (err: any) {
      setParseError(err.message || "Validation failed");
    } finally {
      setValidating(false);
    }
  };

  const handleDiscardEdits = () => {
    if (state.applied) {
      dispatch({
        type: "EDIT_DRAFT",
        draft: structuredClone(state.applied.draft),
      });
      setParseError(null);
    }
  };

  const handleExportJson = () => {
    if (!draft) return;
    const blob = new Blob([JSON.stringify(draft, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${draft.name || "timetable_instance"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportJson = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const text = evt.target?.result as string;
        const parsed = JSON.parse(text);
        if (parsed && typeof parsed === "object" && Array.isArray(parsed.days)) {
          dispatch({
            type: "SET_DRAFT",
            draft: parsed as InstanceDraft,
            source: `Imported JSON: ${file.name}`,
          });
          setParseError(null);
        } else {
          setParseError("Invalid draft JSON structure");
        }
      } catch {
        setParseError("Could not parse JSON file");
      }
    };
    reader.readAsText(file);
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Data Management</h1>
        <p className="page-caption">
          Load instances from sample datasets, upload CSV files, or generate benchmark problems.
        </p>
      </div>

      {/* 1. SOURCE PANEL */}
      <div className="panel">
        <div className="panel-title">
          <span>1. Load or Generate Instance</span>
        </div>

        <div className="tabs-header">
          <button
            type="button"
            className={`tab-btn ${sourceTab === "sample" ? "active" : ""}`}
            onClick={() => setSourceTab("sample")}
          >
            Sample Instance
          </button>
          <button
            type="button"
            className={`tab-btn ${sourceTab === "upload" ? "active" : ""}`}
            onClick={() => setSourceTab("upload")}
          >
            Upload CSV
          </button>
          <button
            type="button"
            className={`tab-btn ${sourceTab === "generate" ? "active" : ""}`}
            onClick={() => setSourceTab("generate")}
          >
            Random Generator
          </button>
        </div>

        {/* Tab 1: Sample */}
        {sourceTab === "sample" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
              <label htmlFor="sample-select" style={{ fontWeight: 600, fontSize: "0.9rem" }}>
                Select Sample:
              </label>
              <select
                id="sample-select"
                className="table-input"
                style={{ width: "240px" }}
                value={selectedSample}
                onChange={(e) => setSelectedSample(e.target.value)}
              >
                {samples.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="btn btn-primary"
                disabled={loadingSample || !selectedSample}
                onClick={handleLoadSample}
              >
                {loadingSample ? "Loading…" : "Load Sample"}
              </button>
            </div>

            {selectedSample && (
              <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                {samples.find((s) => s.name === selectedSample)?.description}
              </p>
            )}
          </div>
        )}

        {/* Tab 2: Upload CSV */}
        {sourceTab === "upload" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div>
              <label
                htmlFor="csv-upload-input"
                style={{ display: "block", fontWeight: 600, fontSize: "0.9rem", marginBottom: "6px" }}
              >
                Select CSV files (days, slots, teachers, courses, divisions, rooms):
              </label>
              <input
                id="csv-upload-input"
                type="file"
                multiple
                accept=".csv"
                onChange={handleFilesSelected}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Detected Files:</span>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {CSV_REQUIRED_NAMES.map((name) => {
                  const found = selectedFiles.some((f) => f.name.toLowerCase() === name);
                  return (
                    <span
                      key={name}
                      className={`checklist-item ${found ? "found" : "missing"}`}
                    >
                      {found ? "✔" : "○"} {name}
                    </span>
                  );
                })}
                {CSV_OPTIONAL_NAMES.map((name) => {
                  const found = selectedFiles.some((f) => f.name.toLowerCase() === name);
                  return (
                    <span
                      key={name}
                      className={`checklist-item ${found ? "found" : "missing"}`}
                    >
                      {found ? "✔" : "○"} {name} (optional)
                    </span>
                  );
                })}
              </div>
            </div>

            {uploadError && (
              <div className="status-banner tone-red" role="alert">
                <span>✖</span>
                <span>{uploadError}</span>
              </div>
            )}

            <div>
              <button
                type="button"
                className="btn btn-primary"
                disabled={uploading || selectedFiles.length === 0}
                onClick={handleUploadCsv}
              >
                {uploading ? "Parsing CSVs…" : "Read Files & Load Draft"}
              </button>
            </div>
          </div>
        )}

        {/* Tab 3: Generator */}
        {sourceTab === "generate" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
              <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>Presets:</span>
              {(["small", "medium", "large"] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  className={`btn ${selectedPresetName === p ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => setSelectedPresetName(p)}
                  style={{ textTransform: "capitalize" }}
                >
                  {p}
                </button>
              ))}

              <label style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "0.9rem", marginLeft: "8px" }}>
                Seed:
                <input
                  type="number"
                  className="table-input"
                  style={{ width: "80px" }}
                  value={genSeed}
                  onChange={(e) => setGenSeed(parseInt(e.target.value, 10) || 1)}
                />
              </label>

              <button
                type="button"
                className="btn btn-primary"
                disabled={generating}
                onClick={handleGenerateInstance}
              >
                {generating ? "Generating…" : "Generate Instance"}
              </button>
            </div>

            <details
              open={showAdvancedGen}
              onToggle={(e) => setShowAdvancedGen((e.target as HTMLDetailsElement).open)}
              style={{ marginTop: "8px" }}
            >
              <summary style={{ cursor: "pointer", fontSize: "0.85rem", color: "var(--primary)" }}>
                Advanced Generator Parameters
              </summary>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: "12px",
                  marginTop: "12px",
                }}
              >
                <label style={{ fontSize: "0.85rem" }}>
                  Days:
                  <input
                    type="number"
                    className="table-input"
                    value={customGenConfig.num_days}
                    onChange={(e) =>
                      setCustomGenConfig({ ...customGenConfig, num_days: parseInt(e.target.value, 10) || 5 })
                    }
                  />
                </label>
                <label style={{ fontSize: "0.85rem" }}>
                  Slots/Day:
                  <input
                    type="number"
                    className="table-input"
                    value={customGenConfig.slots_per_day}
                    onChange={(e) =>
                      setCustomGenConfig({ ...customGenConfig, slots_per_day: parseInt(e.target.value, 10) || 6 })
                    }
                  />
                </label>
                <label style={{ fontSize: "0.85rem" }}>
                  Divisions:
                  <input
                    type="number"
                    className="table-input"
                    value={customGenConfig.num_divisions}
                    onChange={(e) =>
                      setCustomGenConfig({ ...customGenConfig, num_divisions: parseInt(e.target.value, 10) || 2 })
                    }
                  />
                </label>
                <label style={{ fontSize: "0.85rem" }}>
                  Teachers:
                  <input
                    type="number"
                    className="table-input"
                    value={customGenConfig.num_teachers}
                    onChange={(e) =>
                      setCustomGenConfig({ ...customGenConfig, num_teachers: parseInt(e.target.value, 10) || 6 })
                    }
                  />
                </label>
                <label style={{ fontSize: "0.85rem" }}>
                  Courses:
                  <input
                    type="number"
                    className="table-input"
                    value={customGenConfig.num_courses}
                    onChange={(e) =>
                      setCustomGenConfig({ ...customGenConfig, num_courses: parseInt(e.target.value, 10) || 8 })
                    }
                  />
                </label>
                <label style={{ fontSize: "0.85rem" }}>
                  Rooms:
                  <input
                    type="number"
                    className="table-input"
                    value={customGenConfig.num_rooms}
                    onChange={(e) =>
                      setCustomGenConfig({ ...customGenConfig, num_rooms: parseInt(e.target.value, 10) || 4 })
                    }
                  />
                </label>
                <label style={{ fontSize: "0.85rem" }}>
                  Availability Density (0–1):
                  <input
                    type="number"
                    step="0.05"
                    min="0.1"
                    max="1.0"
                    className="table-input"
                    value={customGenConfig.availability_density}
                    onChange={(e) =>
                      setCustomGenConfig({ ...customGenConfig, availability_density: parseFloat(e.target.value) || 0.8 })
                    }
                  />
                </label>
                <label style={{ fontSize: "0.85rem" }}>
                  Tightness (0–1):
                  <input
                    type="number"
                    step="0.05"
                    min="0.1"
                    max="1.0"
                    className="table-input"
                    value={customGenConfig.tightness}
                    onChange={(e) =>
                      setCustomGenConfig({ ...customGenConfig, tightness: parseFloat(e.target.value) || 0.6 })
                    }
                  />
                </label>
              </div>
            </details>
          </div>
        )}
      </div>

      {/* 2. EDITOR PANEL */}
      {draft ? (
        <div className="panel">
          <div className="panel-title">
            <span>
              2. Edit Instance: <em>{draft.name}</em> {state.dirty && <span style={{ color: "var(--status-yellow-text)" }}>(Modified)</span>}
            </span>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleExportJson}
                style={{ padding: "4px 10px", fontSize: "0.8rem" }}
              >
                Export JSON
              </button>
              <label
                className="btn btn-secondary"
                style={{ padding: "4px 10px", fontSize: "0.8rem", cursor: "pointer" }}
              >
                Import JSON
                <input
                  type="file"
                  accept=".json"
                  style={{ display: "none" }}
                  onChange={handleImportJson}
                />
              </label>
            </div>
          </div>

          <div className="tabs-header">
            <button
              type="button"
              className={`tab-btn ${editorTab === "days_slots" ? "active" : ""}`}
              onClick={() => setEditorTab("days_slots")}
            >
              Days &amp; Slots ({draft.days.length}d × {draft.slots.length}s)
            </button>
            <button
              type="button"
              className={`tab-btn ${editorTab === "teachers" ? "active" : ""}`}
              onClick={() => setEditorTab("teachers")}
            >
              Teachers ({draft.teachers.length})
            </button>
            <button
              type="button"
              className={`tab-btn ${editorTab === "courses" ? "active" : ""}`}
              onClick={() => setEditorTab("courses")}
            >
              Courses ({draft.courses.length})
            </button>
            <button
              type="button"
              className={`tab-btn ${editorTab === "divisions" ? "active" : ""}`}
              onClick={() => setEditorTab("divisions")}
            >
              Divisions ({draft.divisions.length})
            </button>
            <button
              type="button"
              className={`tab-btn ${editorTab === "rooms" ? "active" : ""}`}
              onClick={() => setEditorTab("rooms")}
            >
              Rooms ({draft.rooms.length})
            </button>
            <button
              type="button"
              className={`tab-btn ${editorTab === "fixed" ? "active" : ""}`}
              onClick={() => setEditorTab("fixed")}
            >
              Fixed Assignments ({draft.fixed_assignments.length})
            </button>
          </div>

          {/* Days & Slots */}
          {editorTab === "days_slots" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
              <EditableTable<{ name: string }>
                tableName="Days"
                rows={draft.days.map((d) => ({ name: d }))}
                columns={[{ key: "name", header: "Day Name", kind: "text", required: true }]}
                onChange={(newRows) =>
                  dispatch({
                    type: "EDIT_DRAFT",
                    draft: { ...draft, days: newRows.map((r) => r.name) },
                  })
                }
                makeEmptyRow={() => ({ name: "" })}
                rowKey={(r, i) => `${r.name}-${i}`}
              />

              <EditableTable<SlotDef>
                tableName="Slots"
                rows={draft.slots}
                columns={[
                  { key: "start", header: "Start Time", kind: "text", required: true, placeholder: "09:00" },
                  { key: "end", header: "End Time", kind: "text", required: true, placeholder: "10:00" },
                ]}
                onChange={(newRows) =>
                  dispatch({
                    type: "EDIT_DRAFT",
                    draft: { ...draft, slots: newRows },
                  })
                }
                makeEmptyRow={() => ({ start: "09:00", end: "10:00" })}
                rowKey={(r, i) => `${r.start}-${i}`}
              />
            </div>
          )}

          {/* Teachers */}
          {editorTab === "teachers" && (
            <EditableTable<TeacherRow>
              tableName="Teachers"
              rows={draft.teachers}
              columns={teacherColumns}
              onChange={(newRows) =>
                dispatch({
                  type: "EDIT_DRAFT",
                  draft: { ...draft, teachers: newRows },
                })
              }
              makeEmptyRow={() => ({
                teacher_id: "",
                teacher_name: "",
                unavailable_slots: [],
                preferred_slots: [],
                max_daily_sessions: null,
              })}
              rowKey={(r, i) => r.teacher_id || String(i)}
              days={draft.days}
              slots={draft.slots}
            />
          )}

          {/* Courses */}
          {editorTab === "courses" && (
            <EditableTable<CourseRow>
              tableName="Courses"
              rows={draft.courses}
              columns={courseColumns}
              onChange={(newRows) =>
                dispatch({
                  type: "EDIT_DRAFT",
                  draft: { ...draft, courses: newRows },
                })
              }
              makeEmptyRow={() => ({
                course_id: "",
                course_name: "",
                teacher_id: draft.teachers[0]?.teacher_id || "",
                sessions_per_week: 1,
                duration_slots: 1,
                room_types: ["lecture"],
                eligible_divisions: [],
              })}
              rowKey={(r, i) => r.course_id || String(i)}
            />
          )}

          {/* Divisions */}
          {editorTab === "divisions" && (
            <EditableTable<DivisionRow>
              tableName="Divisions"
              rows={draft.divisions}
              columns={divisionColumns}
              onChange={(newRows) =>
                dispatch({
                  type: "EDIT_DRAFT",
                  draft: { ...draft, divisions: newRows },
                })
              }
              makeEmptyRow={() => ({
                division_id: "",
                division_name: "",
                student_count: 30,
                enrolled_courses: [],
              })}
              rowKey={(r, i) => r.division_id || String(i)}
            />
          )}

          {/* Rooms */}
          {editorTab === "rooms" && (
            <EditableTable<RoomRow>
              tableName="Rooms"
              rows={draft.rooms}
              columns={roomColumns}
              onChange={(newRows) =>
                dispatch({
                  type: "EDIT_DRAFT",
                  draft: { ...draft, rooms: newRows },
                })
              }
              makeEmptyRow={() => ({
                room_id: "",
                room_name: "",
                room_type: "lecture",
                capacity: 40,
                unavailable_slots: [],
              })}
              rowKey={(r, i) => r.room_id || String(i)}
              days={draft.days}
              slots={draft.slots}
            />
          )}

          {/* Fixed Assignments */}
          {editorTab === "fixed" && (
            <EditableTable<FixedRow>
              tableName="Fixed Assignments"
              rows={draft.fixed_assignments}
              columns={fixedColumns}
              onChange={(newRows) =>
                dispatch({
                  type: "EDIT_DRAFT",
                  draft: { ...draft, fixed_assignments: newRows },
                })
              }
              makeEmptyRow={() => ({
                session_id: "",
                day_name: draft.days[0] || "",
                start_time: draft.slots[0]?.start || "",
                room_id: draft.rooms[0]?.room_id || "",
              })}
              rowKey={(r, i) => `${r.session_id}-${i}`}
            />
          )}

          {/* Action Bar */}
          <div className="action-bar">
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              <button
                type="button"
                className="btn btn-primary"
                disabled={validating}
                onClick={handleValidateAndApply}
              >
                {validating ? "Validating…" : "Validate & Apply"}
              </button>

              <button
                type="button"
                className="btn btn-secondary"
                disabled={!state.dirty || !state.applied}
                onClick={handleDiscardEdits}
                title="Discard edits and restore last applied draft"
              >
                Discard Edits
              </button>
            </div>

            {state.dirty && (
              <span style={{ fontSize: "0.85rem", color: "var(--status-yellow-text)" }}>
                ⚠ You have unvalidated edits. Press "Validate &amp; Apply" to accept them.
              </span>
            )}
          </div>

          {/* 3. ISSUES TABLE */}
          <IssuesTable
            issues={state.applied?.issues || []}
            parseError={parseError}
            sessionsCount={state.applied?.summary.sessions}
          />
        </div>
      ) : (
        <div className="panel" style={{ textAlign: "center", padding: "40px 20px" }}>
          <p style={{ color: "var(--text-muted)" }}>
            No instance loaded. Choose a sample instance above or upload CSV spreadsheets to begin.
          </p>
        </div>
      )}
    </div>
  );
}
