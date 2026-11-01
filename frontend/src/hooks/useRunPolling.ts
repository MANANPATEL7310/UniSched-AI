import { useState, useEffect } from "react";
import { getRun } from "../api/client";
import type { Progress, RunResponse } from "../api/types";

export function useRunPolling(
  runId: string | null,
  onFinished: (r: RunResponse) => void
) {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) {
      setProgress(null);
      setError(null);
      return;
    }

    let stopped = false;
    let failures = 0;
    let timer: number | undefined;
    const ctrl = new AbortController();

    const tick = async () => {
      try {
        const r = await getRun(runId, ctrl.signal);
        if (stopped) return;
        failures = 0;
        setProgress(r.progress);
        if (r.state !== "running") {
          onFinished(r);
          return;
        }
      } catch (e: unknown) {
        if (stopped) return;
        failures += 1;
        if (failures >= 5) {
          setError((e as Error).message);
          return;
        }
      }
      if (!stopped) {
        timer = window.setTimeout(tick, 500);
      }
    };

    tick();

    return () => {
      stopped = true;
      ctrl.abort();
      window.clearTimeout(timer);
    };
  }, [runId]);

  return { progress, error };
}

