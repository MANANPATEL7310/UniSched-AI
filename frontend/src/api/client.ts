import type {
  BenchmarkRequest,
  BenchmarkResponse,
  BenchmarkRow,
  GeneratorConfigDto,
  InstanceDraft,
  RunConfigDto,
  RunResponse,
  SampleInfo,
  SavedResultInfo,
  ValidateResponse,
} from "./types.js";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) || "/api";

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init?: RequestInit & { signal?: AbortSignal }
): Promise<T> {
  let res: Response;
  const isFormData = init?.body instanceof FormData;
  const headers: HeadersInit = {
    ...(!isFormData ? { "Content-Type": "application/json" } : {}),
    ...(init?.headers || {}),
  };

  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers,
    });
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw err;
    }
    throw new ApiError(
      "NETWORK",
      "Cannot reach the server. Is the backend running on port 8000?",
      0
    );
  }

  if (!res.ok) {
    let body: any = null;
    try {
      body = await res.json();
    } catch {
      // not JSON
    }
    const e = body?.error;
    throw new ApiError(
      e?.code ?? `HTTP_${res.status}`,
      e?.message ?? res.statusText,
      res.status,
      e?.details
    );
  }

  return (await res.json()) as T;
}

export async function health(): Promise<{ status: string; version: string }> {
  return request<{ status: string; version: string }>("/health");
}

export async function listSamples(): Promise<SampleInfo[]> {
  return request<SampleInfo[]>("/samples");
}

export async function getSample(name: string): Promise<InstanceDraft> {
  return request<InstanceDraft>(`/samples/${encodeURIComponent(name)}`);
}

export async function uploadCsv(files: File[]): Promise<InstanceDraft> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  return request<InstanceDraft>("/instances/upload-csv", {
    method: "POST",
    body: formData,
  });
}

export async function getPresets(): Promise<Record<string, GeneratorConfigDto>> {
  return request<Record<string, GeneratorConfigDto>>("/generator/presets");
}

export async function generateInstance(
  cfg: GeneratorConfigDto
): Promise<InstanceDraft> {
  return request<InstanceDraft>("/instances/generate", {
    method: "POST",
    body: JSON.stringify(cfg),
  });
}

export async function validateDraft(
  draft: InstanceDraft
): Promise<ValidateResponse> {
  return request<ValidateResponse>("/instances/validate", {
    method: "POST",
    body: JSON.stringify(draft),
  });
}

export async function startRun(
  draft: InstanceDraft,
  cfg: RunConfigDto
): Promise<{ run_id: string }> {
  return request<{ run_id: string }>("/runs", {
    method: "POST",
    body: JSON.stringify({ draft, config: cfg }),
  });
}

export async function getRun(
  id: string,
  signal?: AbortSignal
): Promise<RunResponse> {
  return request<RunResponse>(`/runs/${encodeURIComponent(id)}`, {
    signal,
  });
}

export async function cancelRun(id: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/runs/${encodeURIComponent(id)}/cancel`, {
    method: "POST",
  });
}

export function timetableCsvUrl(id: string): string {
  return `${BASE}/runs/${encodeURIComponent(id)}/timetable.csv`;
}

export async function startBenchmark(
  req: BenchmarkRequest
): Promise<{ job_id: string }> {
  return request<{ job_id: string }>("/benchmarks", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function getBenchmark(
  id: string,
  signal?: AbortSignal
): Promise<BenchmarkResponse> {
  return request<BenchmarkResponse>(`/benchmarks/${encodeURIComponent(id)}`, {
    signal,
  });
}

export async function cancelBenchmark(id: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/benchmarks/${encodeURIComponent(id)}/cancel`, {
    method: "POST",
  });
}

export async function listSavedResults(): Promise<SavedResultInfo[]> {
  return request<SavedResultInfo[]>("/benchmarks/results");
}

export async function getSavedResult(name: string): Promise<BenchmarkRow[]> {
  return request<BenchmarkRow[]>(`/benchmarks/results/${encodeURIComponent(name)}`);
}

export async function repair(payload: unknown): Promise<unknown> {
  return request<unknown>("/repair", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
