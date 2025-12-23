// Types for evaluation jobs and results

export type RetrievalMethod = "basic" | "multi-query" | "hybrid";
export type JobStatus = "queued" | "running" | "completed" | "failed";

export interface EvaluationRequest {
  dataset_id: string;
  retrieval_method: RetrievalMethod;
  k_values: number[];
  rag_service_url?: string;
}

export interface EvaluationJob {
  job_id: string;
  dataset_id: string;
  retrieval_method: RetrievalMethod;
  k_values: number[];
  status: JobStatus;
  progress?: number; // 0-100
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface MetricsAtK {
  values: Record<string, number>; // e.g., {"1": 0.85, "3": 0.78, ...}
}

export interface AggregateMetrics {
  ndcg: MetricsAtK;
  map: MetricsAtK;
  mrr: MetricsAtK;
  total_queries: number;
}

export interface PerQueryMetrics {
  query: string;
  ndcg: Record<string, number>;
  map: Record<string, number>;
  mrr: Record<string, number>;
  retrieved_docs: string[];
  expected_docs: string[];
}

export interface EvaluationResults {
  job_id: string;
  dataset_id: string;
  dataset_name: string;
  retrieval_method: RetrievalMethod;
  k_values: number[];
  aggregate_metrics: AggregateMetrics;
  per_query_metrics: PerQueryMetrics[];
  created_at: string;
}

export interface JobListResponse {
  jobs: EvaluationJob[];
  total: number;
}
