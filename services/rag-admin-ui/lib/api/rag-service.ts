// API client for RAG service

import type {
  QueryRequest,
  QueryResponse,
  UploadResult,
  DocumentListResponse,
} from "@/lib/types";

const BASE_URL = process.env.NEXT_PUBLIC_RAG_SERVICE_URL || "http://localhost:8000";

class RAGServiceClient {
  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${BASE_URL}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...options?.headers,
        },
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({
          detail: `HTTP ${response.status}: ${response.statusText}`,
        }));
        throw new Error(error.detail || error.message || "Request failed");
      }

      return response.json();
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error("Unknown error occurred");
    }
  }

  // Query/Retrieval

  async queryBasic(query: string, top_k = 5): Promise<QueryResponse> {
    return this.request("/api/v1/retrieve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k }),
    });
  }

  async queryMulti(query: string, top_k = 5): Promise<QueryResponse> {
    return this.request("/api/v1/multi-query-retrieve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k }),
    });
  }

  async queryHybrid(query: string, top_k = 5): Promise<QueryResponse> {
    return this.request("/api/v1/retrieve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k, search_type: "hybrid" }),
    });
  }

  async query(request: QueryRequest): Promise<QueryResponse> {
    switch (request.retrieval_method) {
      case "basic":
        return this.queryBasic(request.query, request.top_k);
      case "multi-query":
        return this.queryMulti(request.query, request.top_k);
      case "hybrid":
        return this.queryHybrid(request.query, request.top_k);
      default:
        throw new Error(`Unknown retrieval method: ${request.retrieval_method}`);
    }
  }

  // Data Upload

  async uploadFiles(files: File[]): Promise<UploadResult[]> {
    const results: UploadResult[] = [];

    for (const file of files) {
      const formData = new FormData();
      formData.append("file", file);

      try {
        const result = await this.request<UploadResult>("/api/v1/ingest", {
          method: "POST",
          body: formData,
        });
        results.push(result);
      } catch (error) {
        // If upload fails, add failed result
        results.push({
          status: "failed",
          file_name: file.name,
          chunks_created: 0,
          processing_time_ms: 0,
          metadata: { error: error instanceof Error ? error.message : "Upload failed" },
        });
      }
    }

    return results;
  }

  async uploadDirectory(files: File[]): Promise<UploadResult[]> {
    // Directory upload uses the same ingest endpoint
    return this.uploadFiles(files);
  }

  // Documents

  async listDocuments(
    page = 1,
    limit = 50,
    search?: string
  ): Promise<DocumentListResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
      ...(search && { search }),
    });

    return this.request(`/api/v1/documents?${params.toString()}`);
  }

  // Stats

  async getStats(): Promise<{ total_documents: number; total_chunks: number; collection_name: string }> {
    return this.request("/api/v1/stats");
  }

  // Health check

  async healthCheck(): Promise<{ status: string }> {
    return this.request("/api/v1/health");
  }
}

export const ragServiceClient = new RAGServiceClient();
