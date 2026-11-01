import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EditableTable, type Column } from "../components/EditableTable.tsx";

interface TestRow {
  id: string;
  name: string;
  count: number | null;
}

describe("EditableTable", () => {
  const columns: Column<TestRow>[] = [
    { key: "id", header: "ID", kind: "text", isId: true, required: true },
    { key: "name", header: "Name", kind: "text", required: true },
    { key: "count", header: "Count", kind: "int", min: 1 },
  ];

  const initialRows: TestRow[] = [
    { id: "T1", name: "Teacher 1", count: 2 },
    { id: "T2", name: "Teacher 2", count: 4 },
  ];

  it("renders table with data rows and columns", () => {
    render(
      <EditableTable<TestRow>
        tableName="Test Teachers"
        rows={initialRows}
        columns={columns}
        onChange={vi.fn()}
        makeEmptyRow={() => ({ id: "", name: "", count: 1 })}
        rowKey={(r) => r.id}
      />
    );

    expect(screen.getByText(/Test Teachers \(2 rows\)/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue("Teacher 1")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Teacher 2")).toBeInTheDocument();
  });

  it("adds an empty row when Add Row is clicked", () => {
    const handleChange = vi.fn();
    render(
      <EditableTable<TestRow>
        tableName="Test Teachers"
        rows={initialRows}
        columns={columns}
        onChange={handleChange}
        makeEmptyRow={() => ({ id: "NEW", name: "New One", count: 1 })}
        rowKey={(r) => r.id}
      />
    );

    fireEvent.click(screen.getByText("+ Add Row"));
    expect(handleChange).toHaveBeenCalledWith([
      ...initialRows,
      { id: "NEW", name: "New One", count: 1 },
    ]);
  });

  it("calls onChange when cell input changes", () => {
    const handleChange = vi.fn();
    render(
      <EditableTable<TestRow>
        tableName="Test Teachers"
        rows={initialRows}
        columns={columns}
        onChange={handleChange}
        makeEmptyRow={() => ({ id: "", name: "", count: 1 })}
        rowKey={(r) => r.id}
      />
    );

    const nameInput = screen.getByDisplayValue("Teacher 1");
    fireEvent.change(nameInput, { target: { value: "Updated Name" } });

    expect(handleChange).toHaveBeenCalledWith([
      { id: "T1", name: "Updated Name", count: 2 },
      initialRows[1],
    ]);
  });

  it("requires confirmation to delete a non-empty row", () => {
    const handleChange = vi.fn();
    render(
      <EditableTable<TestRow>
        tableName="Test Teachers"
        rows={initialRows}
        columns={columns}
        onChange={handleChange}
        makeEmptyRow={() => ({ id: "", name: "", count: 1 })}
        rowKey={(r) => r.id}
      />
    );

    const deleteButtons = screen.getAllByText("✕");
    fireEvent.click(deleteButtons[0]!);

    // Should prompt for confirmation
    expect(screen.getByText("Delete?")).toBeInTheDocument();
    expect(handleChange).not.toHaveBeenCalled();

    // Confirm deletion
    fireEvent.click(screen.getByText("Delete?"));
    expect(handleChange).toHaveBeenCalledWith([initialRows[1]]);
  });

  it("highlights duplicate IDs with input-error class", () => {
    const rowsWithDup: TestRow[] = [
      { id: "DUP", name: "Row 1", count: 1 },
      { id: "DUP", name: "Row 2", count: 2 },
    ];

    render(
      <EditableTable<TestRow>
        tableName="Test Dups"
        rows={rowsWithDup}
        columns={columns}
        onChange={vi.fn()}
        makeEmptyRow={() => ({ id: "", name: "", count: 1 })}
        rowKey={(r, i) => `${r.id}-${i}`}
      />
    );

    const inputs = screen.getAllByDisplayValue("DUP");
    expect(inputs[0]).toHaveClass("input-error");
    expect(inputs[1]).toHaveClass("input-error");
  });
});
