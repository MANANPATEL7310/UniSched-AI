import { useMemo, useState } from "react";
import { ConfirmButton } from "./ConfirmButton.js";
import { AvailabilityGrid } from "./AvailabilityGrid.js";
import type { SlotDef } from "../api/types.js";

export type ColumnKind =
  | "text"
  | "int"
  | "select"
  | "multiselect"
  | "availability"
  | "readonly";

export interface Column<T> {
  key: keyof T & string;
  header: string;
  kind: ColumnKind;
  min?: number;
  options?: { value: string; label: string }[];
  placeholder?: string;
  required?: boolean;
  isId?: boolean;
  availabilityModalTitle?: (row: T) => string;
}

interface EditableTableProps<T> {
  rows: T[];
  columns: Column<T>[];
  onChange: (newRows: T[]) => void;
  makeEmptyRow: () => T;
  rowKey: (row: T, index: number) => string;
  tableName: string;
  days?: string[];
  slots?: SlotDef[];
}

export function EditableTable<T extends Record<string, any>>({
  rows,
  columns,
  onChange,
  makeEmptyRow,
  rowKey,
  tableName,
  days = [],
  slots = [],
}: EditableTableProps<T>) {
  const [activeModal, setActiveModal] = useState<{
    rowIndex: number;
    colKey: string;
  } | null>(null);

  const duplicateIdSets = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const col of columns) {
      if (col.isId) {
        const counts = new Map<string, number>();
        for (const row of rows) {
          const val = String(row[col.key] || "").trim();
          if (val) {
            counts.set(val, (counts.get(val) || 0) + 1);
          }
        }
        const dups = new Set<string>();
        for (const [val, count] of counts.entries()) {
          if (count > 1) dups.add(val);
        }
        map.set(col.key, dups);
      }
    }
    return map;
  }, [rows, columns]);

  const handleCellChange = (rowIndex: number, colKey: string, value: any) => {
    const updated = rows.map((r, i) => {
      if (i === rowIndex) {
        return { ...r, [colKey]: value };
      }
      return r;
    });
    onChange(updated);
  };

  const handleAddRow = () => {
    onChange([...rows, makeEmptyRow()]);
  };

  const handleDeleteRow = (index: number) => {
    onChange(rows.filter((_, i) => i !== index));
  };

  const isRowEmpty = (row: T): boolean => {
    return Object.entries(row).every(([_, v]) => {
      if (Array.isArray(v)) return v.length === 0;
      return v === "" || v === null || v === undefined;
    });
  };

  return (
    <div className="editable-table-container">
      <div className="editable-table-toolbar">
        <span className="editable-table-title">
          {tableName} ({rows.length} row{rows.length === 1 ? "" : "s"})
        </span>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleAddRow}
          style={{ padding: "4px 12px", fontSize: "0.85rem" }}
        >
          + Add Row
        </button>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table className="editable-table">
          <thead>
            <tr>
              <th scope="col" style={{ width: "40px", textAlign: "center" }}>
                #
              </th>
              {columns.map((col) => (
                <th key={col.key} scope="col">
                  {col.header}
                  {col.required && <span style={{ color: "var(--status-red-text)", marginLeft: "2px" }}>*</span>}
                </th>
              ))}
              <th scope="col" style={{ width: "80px", textAlign: "center" }}>
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length + 2}
                  style={{ textAlign: "center", padding: "24px", color: "var(--text-muted)" }}
                >
                  No rows. Click "+ Add Row" to create one.
                </td>
              </tr>
            ) : (
              rows.map((row, rIdx) => {
                const empty = isRowEmpty(row);
                return (
                  <tr key={rowKey(row, rIdx)}>
                    <td style={{ textAlign: "center", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      {rIdx + 1}
                    </td>

                    {columns.map((col) => {
                      const val = row[col.key];
                      const dupSet = duplicateIdSets.get(col.key);
                      const isDuplicate = col.isId && val && dupSet?.has(String(val).trim());
                      const isEmptyRequired = col.required && (val === "" || val === null || val === undefined);
                      const isBelowMin =
                        col.kind === "int" &&
                        col.min !== undefined &&
                        val !== null &&
                        typeof val === "number" &&
                        val < col.min;

                      const hasError = isDuplicate || isEmptyRequired || isBelowMin;
                      const errorTitle = isDuplicate
                        ? `Duplicate ID "${val}"`
                        : isEmptyRequired
                        ? "This field is required"
                        : isBelowMin
                        ? `Minimum value is ${col.min}`
                        : undefined;

                      return (
                        <td key={col.key}>
                          {col.kind === "readonly" ? (
                            <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                              {String(val ?? "")}
                            </span>
                          ) : col.kind === "text" ? (
                            <input
                              type="text"
                              className={`table-input ${hasError ? "input-error" : ""}`}
                              value={val ?? ""}
                              placeholder={col.placeholder}
                              title={errorTitle}
                              aria-label={`${col.header} row ${rIdx + 1}`}
                              onChange={(e) =>
                                handleCellChange(rIdx, col.key, e.target.value)
                              }
                            />
                          ) : col.kind === "int" ? (
                            <input
                              type="number"
                              className={`table-input ${hasError ? "input-error" : ""}`}
                              value={val === null || val === undefined ? "" : val}
                              min={col.min}
                              placeholder={col.placeholder}
                              title={errorTitle}
                              aria-label={`${col.header} row ${rIdx + 1}`}
                              onChange={(e) => {
                                const raw = e.target.value;
                                if (raw === "") {
                                  handleCellChange(rIdx, col.key, null);
                                } else {
                                  const parsed = parseInt(raw, 10);
                                  handleCellChange(
                                    rIdx,
                                    col.key,
                                    isNaN(parsed) ? null : parsed
                                  );
                                }
                              }}
                            />
                          ) : col.kind === "select" ? (
                            <select
                              className={`table-input ${hasError ? "input-error" : ""}`}
                              value={val ?? ""}
                              title={errorTitle}
                              aria-label={`${col.header} row ${rIdx + 1}`}
                              onChange={(e) =>
                                handleCellChange(rIdx, col.key, e.target.value)
                              }
                            >
                              <option value="">-- Select --</option>
                              {col.options?.map((opt) => (
                                <option key={opt.value} value={opt.value}>
                                  {opt.label}
                                </option>
                              ))}
                            </select>
                          ) : col.kind === "multiselect" ? (
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                              {col.options?.map((opt) => {
                                const selectedList: string[] = Array.isArray(val) ? val : [];
                                const isChecked = selectedList.includes(opt.value);
                                return (
                                  <label
                                    key={opt.value}
                                    style={{
                                      display: "inline-flex",
                                      alignItems: "center",
                                      gap: "4px",
                                      fontSize: "0.8rem",
                                      cursor: "pointer",
                                      background: isChecked
                                        ? "var(--status-blue-bg)"
                                        : "var(--bg-surface-subtle)",
                                      border: `1px solid ${
                                        isChecked
                                          ? "var(--status-blue-border)"
                                          : "var(--border)"
                                      }`,
                                      borderRadius: "var(--radius-sm)",
                                      padding: "2px 6px",
                                    }}
                                  >
                                    <input
                                      type="checkbox"
                                      checked={isChecked}
                                      onChange={() => {
                                        const next = isChecked
                                          ? selectedList.filter((x) => x !== opt.value)
                                          : [...selectedList, opt.value];
                                        handleCellChange(rIdx, col.key, next);
                                      }}
                                    />
                                    <span>{opt.label}</span>
                                  </label>
                                );
                              })}
                            </div>
                          ) : col.kind === "availability" ? (
                            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                              <button
                                type="button"
                                className="btn btn-secondary"
                                style={{ padding: "2px 8px", fontSize: "0.8rem" }}
                                onClick={() =>
                                  setActiveModal({ rowIndex: rIdx, colKey: col.key })
                                }
                              >
                                Edit ({(Array.isArray(val) ? val.length : 0)} slots)
                              </button>
                            </div>
                          ) : null}
                        </td>
                      );
                    })}

                    <td style={{ textAlign: "center" }}>
                      <ConfirmButton
                        onConfirm={() => handleDeleteRow(rIdx)}
                        needsConfirm={!empty}
                        title={`Delete row ${rIdx + 1}`}
                        confirmLabel="Delete?"
                      >
                        ✕
                      </ConfirmButton>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {activeModal !== null && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal-content">
            <AvailabilityGrid
              days={days}
              slots={slots}
              value={rows[activeModal.rowIndex]?.[activeModal.colKey] || []}
              label={
                columns.find((c) => c.key === activeModal.colKey)
                  ?.availabilityModalTitle?.(rows[activeModal.rowIndex]!) ||
                "Configure Availability"
              }
              onChange={(next) =>
                handleCellChange(activeModal.rowIndex, activeModal.colKey, next)
              }
              onClose={() => setActiveModal(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
