import { useState, useEffect } from "react";
import { getBenchmark } from "../api/client.js";
import type { BenchmarkResponse } from "../api/types.js";

export interface BenchmarkProgress {
  done: number;
  total: number;
}

export function useBenchmarkPolling(
  jobId: string | null,
  onFinished: (res: BenchmarkResponse) => void
) {
  const [progress, setProgress] = useState<BenchmarkProgress | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) {
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
        const r = await getBenchmark(jobId, ctrl.signal);
        if (stopped) return;
        failures = 0;
        setProgress({ done: r.done, total: r.total });
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
  }, [jobId]);

  return { progress, error };
}
