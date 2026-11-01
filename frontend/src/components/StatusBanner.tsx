import { useApp } from "../state/AppContext.js";
import { deriveStatus, type StatusInfo } from "../lib/status.js";

interface StatusBannerProps {
  info?: StatusInfo;
  running?: boolean;
}

export function StatusBanner({ info, running = false }: StatusBannerProps) {
  const { state } = useApp();
  const status = info ?? deriveStatus(state, running);

  const iconForCode = (code: string) => {
    switch (code) {
      case "VALID":
        return "✔";
      case "INVALID":
      case "INPUT_ERRORS":
      case "ERROR":
        return "✖";
      case "TIMEOUT":
      case "NODE_LIMIT":
      case "UNAPPLIED":
        return "⚠";
      case "INFEASIBLE":
        return "⊘";
      case "RUNNING":
        return "⏳";
      case "CANCELLED":
        return "⏹";
      case "READY":
        return "➜";
      case "NO_DATA":
      default:
        return "ℹ";
    }
  };

  return (
    <div
      className={`status-banner tone-${status.tone}`}
      role="status"
      aria-live="polite"
    >
      <span style={{ fontSize: "1.1rem" }}>{iconForCode(status.code)}</span>
      <span>{status.text}</span>
    </div>
  );
}
