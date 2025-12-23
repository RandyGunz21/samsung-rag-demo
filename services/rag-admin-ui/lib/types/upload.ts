// Types for data upload

export interface UploadProgress {
  filename: string;
  progress: number; // 0-100
  status: "pending" | "uploading" | "completed" | "failed";
  error?: string;
}

export interface UploadResult {
  status: "success" | "failed";
  file_name: string;
  chunks_created: number;
  processing_time_ms: number;
  metadata?: Record<string, unknown>;
}

export interface Document {
  id: string;
  filename: string;
  size: number;
  ingested_at: string;
  chunk_count: number;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  page: number;
  limit: number;
}
