export type RunStatus = "idle" | "running" | "success" | "error";
export type SidebarView = "overview" | "alerts" | "cases" | "threats" | "hunting" | "intel" | "reports" | "exports";

export interface Scores {
  coverage: number; product_readiness: number; real_world: number;
  safety_verdict: string; verdict: string;
  covered_observables?: string[]; missing_observables?: string[];
  production_gaps?: string[];
}

export interface RunResult {
  technique_id: string; mode: string;
  verifier_model?: string;
  verifier_model_role?: string;
  scores: Scores;
  outputs: { red: string; blue: string; response: string; verifier: string };
  artifacts: { sigma: string; splunk: string; raw_red: string; raw_blue: string };
  metrics: any;
  timestamp: number;
  apt_results?: any[]; chain_results?: any[];
}

export interface Health { reachable: boolean; latency_ms?: number; model?: string; error?: string; }