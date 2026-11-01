import { useMemo } from "react";
import type { SlotDef } from "../api/types.js";
import { formatTimeRange, slotKey } from "../lib/slots.js";

interface AvailabilityGridProps {
  days: string[];
  slots: SlotDef[];
  value: string[];
  onChange: (newValue: string[]) => void;
  label: string;
  onClose?: () => void;
}

export function AvailabilityGrid({
  days,
  slots,
  value,
  onChange,
  label,
  onClose,
}: AvailabilityGridProps) {
  const valueSet = useMemo(() => new Set(value), [value]);

  const allValidKeys = useMemo(() => {
    const set = new Set<string>();
    for (const day of days) {
      for (const slot of slots) {
        set.add(slotKey(day, slot.start));
      }
    }
    return set;
  }, [days, slots]);

  const unknownSlots = useMemo(() => {
    return value.filter((v) => !allValidKeys.has(v));
  }, [value, allValidKeys]);

  const handleToggle = (key: string) => {
    if (valueSet.has(key)) {
      onChange(value.filter((v) => v !== key));
    } else {
      onChange([...value, key]);
    }
  };

  const handleSelectAll = () => {
    const newValues = Array.from(new Set([...value, ...allValidKeys]));
    onChange(newValues);
  };

  const handleClear = () => {
    // Retain any unknown slots so user doesn't silently destroy invalid inputs
    onChange([...unknownSlots]);
  };

  const handleToggleDay = (day: string) => {
    const dayKeys = slots.map((s) => slotKey(day, s.start));
    const allSelected = dayKeys.every((k) => valueSet.has(k));
    if (allSelected) {
      const dayKeySet = new Set(dayKeys);
      onChange(value.filter((v) => !dayKeySet.has(v)));
    } else {
      const newKeys = dayKeys.filter((k) => !valueSet.has(k));
      onChange([...value, ...newKeys]);
    }
  };

  return (
    <div className="availability-grid-container" role="region" aria-label={label}>
      <div className="availability-grid-header">
        <div>
          <h4>{label}</h4>
          <span className="availability-grid-count">
            {value.length} slot(s) selected
          </span>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleSelectAll}
            style={{ padding: "4px 10px", fontSize: "0.8rem" }}
          >
            Select All
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleClear}
            style={{ padding: "4px 10px", fontSize: "0.8rem" }}
          >
            Clear
          </button>
          {onClose && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={onClose}
              style={{ padding: "4px 10px", fontSize: "0.8rem" }}
            >
              Done
            </button>
          )}
        </div>
      </div>

      {unknownSlots.length > 0 && (
        <div
          style={{
            padding: "8px 12px",
            marginBottom: "12px",
            fontSize: "0.8rem",
            backgroundColor: "var(--status-yellow-bg)",
            color: "var(--status-yellow-text)",
            border: "1px solid var(--status-yellow-border)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <strong>Unknown slots retained:</strong> {unknownSlots.join(", ")}
        </div>
      )}

      {days.length === 0 || slots.length === 0 ? (
        <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)" }}>
          Define days and slots first in the "Days &amp; Slots" tab.
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="availability-table">
            <thead>
              <tr>
                <th scope="col" style={{ width: "120px" }}>Time Slot</th>
                {days.map((day) => (
                  <th key={day} scope="col">
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                      <span>{day}</span>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => handleToggleDay(day)}
                        style={{ padding: "2px 6px", fontSize: "0.7rem" }}
                        title={`Toggle all slots for ${day}`}
                      >
                        Toggle
                      </button>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {slots.map((slot, sIdx) => {
                const timeLabel = formatTimeRange(slot.start, slot.end);
                return (
                  <tr key={sIdx}>
                    <th scope="row" style={{ fontWeight: 600, fontSize: "0.85rem" }}>
                      {timeLabel}
                    </th>
                    {days.map((day) => {
                      const key = slotKey(day, slot.start);
                      const isChecked = valueSet.has(key);
                      return (
                        <td key={key} style={{ textAlign: "center" }}>
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => handleToggle(key)}
                            aria-label={`${label} on ${day} at ${slot.start}`}
                            style={{ cursor: "pointer", width: "16px", height: "16px" }}
                          />
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
