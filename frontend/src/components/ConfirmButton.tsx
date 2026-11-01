import { useState, type ReactNode } from "react";

interface ConfirmButtonProps {
  onConfirm: () => void;
  children?: ReactNode;
  confirmLabel?: string;
  className?: string;
  title?: string;
  disabled?: boolean;
  needsConfirm?: boolean;
}

export function ConfirmButton({
  onConfirm,
  children = "Delete",
  confirmLabel = "Confirm?",
  className = "btn btn-secondary",
  title,
  disabled = false,
  needsConfirm = true,
}: ConfirmButtonProps) {
  const [confirming, setConfirming] = useState(false);

  if (!needsConfirm) {
    return (
      <button
        type="button"
        className={className}
        title={title}
        disabled={disabled}
        onClick={onConfirm}
      >
        {children}
      </button>
    );
  }

  if (confirming) {
    return (
      <span style={{ display: "inline-flex", gap: "4px", alignItems: "center" }}>
        <button
          type="button"
          className="btn"
          style={{
            padding: "3px 8px",
            fontSize: "0.8rem",
            backgroundColor: "var(--status-red-bg)",
            color: "var(--status-red-text)",
            border: "1px solid var(--status-red-border)",
          }}
          onClick={() => {
            setConfirming(false);
            onConfirm();
          }}
        >
          {confirmLabel}
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          style={{ padding: "3px 8px", fontSize: "0.8rem" }}
          onClick={() => setConfirming(false)}
        >
          Cancel
        </button>
      </span>
    );
  }

  return (
    <button
      type="button"
      className={className}
      title={title}
      disabled={disabled}
      onClick={() => setConfirming(true)}
    >
      {children}
    </button>
  );
}
