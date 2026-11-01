import { useMemo, useState } from "react";
import type { InputIssue } from "../api/types.js";

interface IssuesTableProps {
  issues: InputIssue[];
  parseError?: string | null;
  sessionsCount?: number | null;
}

export function IssuesTable({
  issues,
  parseError,
  sessionsCount,
}: IssuesTableProps) {
  const [sortBySeverityDesc, setSortBySeverityDesc] = useState(true);

  const sortedIssues = useMemo(() => {
    return [...issues].sort((a, b) => {
      if (a.severity === b.severity) {
        return a.code.localeCompare(b.code);
      }
      if (sortBySeverityDesc) {
        return a.severity === "ERROR" ? -1 : 1;
      }
      return a.severity === "WARNING" ? -1 : 1;
    });
  }, [issues, sortBySeverityDesc]);

  const hasErrors = issues.some((i) => i.severity === "ERROR");

  return (
    <div className="issues-container" style={{ marginTop: "20px" }}>
      {parseError && (
        <div
          className="status-banner tone-red"
          style={{ marginBottom: "16px" }}
          role="alert"
        >
          <span>✖</span>
          <span>{parseError}</span>
        </div>
      )}

      {!parseError && hasErrors && (
        <div
          className="status-banner tone-red"
          style={{ marginBottom: "16px" }}
          role="alert"
        >
          <span>✖</span>
          <span>
            Input has {issues.filter((i) => i.severity === "ERROR").length} error(s).
            Fix these errors before generating.
          </span>
        </div>
      )}

      {!parseError && !hasErrors && issues.length > 0 && (
        <div
          className="status-banner tone-yellow"
          style={{ marginBottom: "16px" }}
          role="status"
        >
          <span>⚠</span>
          <span>
            Data accepted with {issues.length} warning(s).{" "}
            {sessionsCount !== null && sessionsCount !== undefined
              ? `${sessionsCount} sessions to schedule.`
              : ""}
          </span>
        </div>
      )}

      {!parseError && issues.length === 0 && sessionsCount !== null && sessionsCount !== undefined && (
        <div
          className="status-banner tone-green"
          style={{ marginBottom: "16px" }}
          role="status"
        >
          <span>✔</span>
          <span>Data accepted: {sessionsCount} sessions to schedule.</span>
        </div>
      )}

      {issues.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table className="issues-table">
            <thead>
              <tr>
                <th
                  scope="col"
                  style={{ width: "120px", cursor: "pointer" }}
                  onClick={() => setSortBySeverityDesc(!sortBySeverityDesc)}
                  title="Click to toggle sorting"
                >
                  Severity {sortBySeverityDesc ? "▼" : "▲"}
                </th>
                <th scope="col" style={{ width: "180px" }}>
                  Code
                </th>
                <th scope="col" style={{ width: "180px" }}>
                  Entity
                </th>
                <th scope="col">Message</th>
              </tr>
            </thead>
            <tbody>
              {sortedIssues.map((issue, idx) => {
                const isError = issue.severity === "ERROR";
                return (
                  <tr key={idx}>
                    <td>
                      <span
                        className={`badge ${isError ? "badge-invalid" : "badge-warning"}`}
                        style={{
                          backgroundColor: isError
                            ? "var(--status-red-bg)"
                            : "var(--status-yellow-bg)",
                          color: isError
                            ? "var(--status-red-text)"
                            : "var(--status-yellow-text)",
                          border: `1px solid ${
                            isError
                              ? "var(--status-red-border)"
                              : "var(--status-yellow-border)"
                          }`,
                        }}
                      >
                        {issue.severity}
                      </span>
                    </td>
                    <td>
                      <code>{issue.code}</code>
                    </td>
                    <td>{issue.entity || "—"}</td>
                    <td>{issue.message}</td>
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
