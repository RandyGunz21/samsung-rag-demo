// API client for RAG-tester service

import type {
  TestDatasetCreate,
  TestDatasetUpdate,
  TestDataset,
  DatasetListResponse,
  EvaluationRequest,
  EvaluationJob,
  EvaluationResults,
  JobListResponse,
} from "@/lib/types";

const BASE_URL = process.env.NEXT_PUBLIC_TESTER_SERVICE_URL || "http://localhost:8001";

class RAGTesterClient {
  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${BASE_URL}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
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

  // Test Datasets

  async createDataset(data: TestDatasetCreate): Promise<{ dataset_id: string; created_at: string }> {
    return this.request("/test-datasets", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async listDatasets(skip = 0, limit = 100): Promise<DatasetListResponse> {
    return this.request(`/test-datasets?skip=${skip}&limit=${limit}`);
  }

  async getDataset(id: string): Promise<TestDataset> {
    return this.request(`/test-datasets/${id}`);
  }

  async updateDataset(id: string, data: TestDatasetUpdate): Promise<void> {
    return this.request(`/test-datasets/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteDataset(id: string): Promise<void> {
    return this.request(`/test-datasets/${id}`, {
      method: "DELETE",
    });
  }

  // Evaluations

  async submitEvaluation(params: EvaluationRequest): Promise<{ job_id: string; status: string; created_at: string }> {
    return this.request("/evaluations", {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async getJobStatus(jobId: string): Promise<EvaluationJob> {
    return this.request(`/evaluations/${jobId}`);
  }

  async getJobResults(jobId: string): Promise<EvaluationResults> {
    return this.request(`/evaluations/${jobId}/results`);
  }

  async listJobs(skip = 0, limit = 50): Promise<JobListResponse> {
    return this.request(`/evaluations?skip=${skip}&limit=${limit}`);
  }

  // Health check

  async healthCheck(): Promise<{ status: string; service: string; version: string }> {
    return this.request("/health");
  }
}

export const ragTesterClient = new RAGTesterClient();
