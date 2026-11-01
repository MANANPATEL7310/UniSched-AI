import type { Algorithm, BenchmarkRow } from "../api/types.js";

export interface AggregatedRow {
  algorithm: Algorithm;
  size_label: string;
  n: number;
  solved: number;
  successRate: number; // 0.0 to 1.0
  mean_runtime_s?: number;
  mean_nodes?: number;
  mean_backtracks?: number;
  mean_soft_penalty?: number;
}

export type MetricKey =
  | "runtime_s"
  | "nodes"
  | "backtracks"
  | "soft_penalty"
  | "successRate";

export interface SeriesPoint {
  num_sessions: number;
  size_label: string;
  A?: number;
  B?: number;
  C?: number;
  D?: number;
}

const SIZE_ORDER: Record<string, number> = {
  tiny: 0,
  small: 1,
  medium: 2,
  large: 3,
};

const ALGO_ORDER: Record<string, number> = {
  A: 0,
  B: 1,
  C: 2,
  D: 3,
};

export function aggregateRows(rows: BenchmarkRow[]): AggregatedRow[] {
  if (!rows || rows.length === 0) {
    return [];
  }

  // Group by algorithm + size_label
  const groups = new Map<string, BenchmarkRow[]>();
  for (const r of rows) {
    const key = `${r.algorithm}__${r.size_label}`;
    let list = groups.get(key);
    if (!list) {
      list = [];
      groups.set(key, list);
    }
    list.push(r);
  }

  const result: AggregatedRow[] = [];

  for (const groupRows of groups.values()) {
    if (groupRows.length === 0) continue;
    const first = groupRows[0]!;
    const n = groupRows.length;
    // Solved runs must be both marked solved and independently valid
    const solvedRows = groupRows.filter((r) => r.solved && r.valid);
    const solvedCount = solvedRows.length;
    const successRate = n > 0 ? solvedCount / n : 0;

    let mean_runtime_s: number | undefined = undefined;
    let mean_nodes: number | undefined = undefined;
    let mean_backtracks: number | undefined = undefined;
    let mean_soft_penalty: number | undefined = undefined;

    if (solvedCount > 0) {
      mean_runtime_s =
        solvedRows.reduce((acc, r) => acc + r.runtime_s, 0) / solvedCount;
      mean_nodes = Math.round(
        solvedRows.reduce((acc, r) => acc + r.nodes, 0) / solvedCount
      );
      mean_backtracks = Math.round(
        solvedRows.reduce((acc, r) => acc + r.backtracks, 0) / solvedCount
      );

      const softRows = solvedRows.filter(
        (r) => r.soft_penalty !== null && !isNaN(r.soft_penalty as number)
      );
      if (softRows.length > 0) {
        mean_soft_penalty =
          softRows.reduce((acc, r) => acc + (r.soft_penalty as number), 0) /
          softRows.length;
      }
    }

    result.push({
      algorithm: first.algorithm,
      size_label: first.size_label,
      n,
      solved: solvedCount,
      successRate,
      mean_runtime_s,
      mean_nodes,
      mean_backtracks,
      mean_soft_penalty,
    });
  }

  // Sort by size then algorithm
  result.sort((a, b) => {
    const sA = SIZE_ORDER[a.size_label] ?? 99;
    const sB = SIZE_ORDER[b.size_label] ?? 99;
    if (sA !== sB) return sA - sB;
    const alA = ALGO_ORDER[a.algorithm] ?? 99;
    const alB = ALGO_ORDER[b.algorithm] ?? 99;
    return alA - alB;
  });

  return result;
}

export function seriesFor(
  metric: MetricKey,
  rows: BenchmarkRow[]
): SeriesPoint[] {
  if (!rows || rows.length === 0) {
    return [];
  }

  // Group by num_sessions
  const sessionGroups = new Map<number, BenchmarkRow[]>();
  for (const r of rows) {
    let list = sessionGroups.get(r.num_sessions);
    if (!list) {
      list = [];
      sessionGroups.set(r.num_sessions, list);
    }
    list.push(r);
  }

  const points: SeriesPoint[] = [];

  for (const [numSessions, groupRows] of sessionGroups.entries()) {
    const size_label = groupRows[0]?.size_label ?? "";
    const pt: SeriesPoint = {
      num_sessions: numSessions,
      size_label,
    };

    const algos: Algorithm[] = ["A", "B", "C", "D"];
    for (const algo of algos) {
      const algoRows = groupRows.filter((r) => r.algorithm === algo);
      if (algoRows.length === 0) continue;

      if (metric === "successRate") {
        const solved = algoRows.filter((r) => r.solved && r.valid).length;
        pt[algo] = Number(((solved / algoRows.length) * 100).toFixed(1));
      } else {
        // Charts 1-3 and soft penalty use ONLY solved runs
        const solvedRows = algoRows.filter((r) => r.solved && r.valid);
        if (solvedRows.length === 0) continue;

        if (metric === "soft_penalty") {
          const softRows = solvedRows.filter(
            (r) => r.soft_penalty !== null && !isNaN(r.soft_penalty as number)
          );
          if (softRows.length > 0) {
            pt[algo] = Number(
              (
                softRows.reduce(
                  (acc, r) => acc + (r.soft_penalty as number),
                  0
                ) / softRows.length
              ).toFixed(2)
            );
          }
        } else {
          const sum = solvedRows.reduce(
            (acc, r) => acc + (r[metric] as number),
            0
          );
          const mean = sum / solvedRows.length;
          pt[algo] = metric === "runtime_s" ? Number(mean.toFixed(4)) : Math.round(mean);
        }
      }
    }

    points.push(pt);
  }

  // Sort ascending by num_sessions
  points.sort((a, b) => a.num_sessions - b.num_sessions);
  return points;
}
