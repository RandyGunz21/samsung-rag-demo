// Types for query interface

export interface QueryRequest {
  query: string;
  retrieval_method: "basic" | "multi-query" | "hybrid";
  top_k?: number;
}

export interface RetrievedDocument {
  content: string;
  metadata: Record<string, unknown>;
  relevance_score: number;
}

export interface QueryResponse {
  documents: RetrievedDocument[];
  query_processed: string;
  search_type_used: string;
  total_found: number;
  processing_time_ms: number;
  generated_queries?: string[]; // For multi-query method
}
