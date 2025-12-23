// Zustand store for evaluation state management

import { create } from "zustand";
import type {
  TestDataset,
  DatasetListItem,
  TestDatasetCreate,
  TestDatasetUpdate,
  EvaluationRequest,
  EvaluationJob,
  EvaluationResults,
} from "@/lib/types";
import { ragTesterClient } from "@/lib/api";

interface EvaluationState {
  // Data
  datasets: DatasetListItem[];
  currentDataset: TestDataset | null;
  jobs: EvaluationJob[];
  currentResults: EvaluationResults | null;

  // Loading states
  isLoading: boolean;
  error: string | null;

  // Polling
  pollingIntervals: Map<string, NodeJS.Timeout>;

  // Actions - Datasets
  fetchDatasets: () => Promise<void>;
  fetchDataset: (id: string) => Promise<TestDataset>;
  createDataset: (data: TestDatasetCreate) => Promise<string>;
  updateDataset: (id: string, data: TestDatasetUpdate) => Promise<void>;
  deleteDataset: (id: string) => Promise<void>;

  // Actions - Evaluations
  submitEvaluation: (params: EvaluationRequest) => Promise<string>;
  fetchJob: (jobId: string) => Promise<void>;
  fetchResults: (jobId: string) => Promise<void>;
  fetchJobs: () => Promise<void>;
  startPolling: (jobId: string, intervalMs?: number) => void;
  stopPolling: (jobId: string) => void;
  stopAllPolling: () => void;

  // Utilities
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useEvaluationStore = create<EvaluationState>((set, get) => ({
  // Initial state
  datasets: [],
  currentDataset: null,
  jobs: [],
  currentResults: null,
  isLoading: false,
  error: null,
  pollingIntervals: new Map(),

  // Dataset actions
  fetchDatasets: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await ragTesterClient.listDatasets();
      set({ datasets: response.datasets, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch datasets",
        isLoading: false,
      });
    }
  },

  fetchDataset: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const dataset = await ragTesterClient.getDataset(id);
      set({ currentDataset: dataset, isLoading: false });
      return dataset; // Return the dataset for component use
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch dataset",
        isLoading: false,
      });
      throw error; // Throw error so component can handle it
    }
  },

  createDataset: async (data: TestDatasetCreate) => {
    set({ isLoading: true, error: null });
    try {
      const response = await ragTesterClient.createDataset(data);
      await get().fetchDatasets(); // Refresh list
      set({ isLoading: false });
      return response.dataset_id;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to create dataset",
        isLoading: false,
      });
      throw error;
    }
  },

  updateDataset: async (id: string, data: TestDatasetUpdate) => {
    set({ isLoading: true, error: null });
    try {
      await ragTesterClient.updateDataset(id, data);
      await get().fetchDatasets(); // Refresh list
      set({ isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to update dataset",
        isLoading: false,
      });
      throw error;
    }
  },

  deleteDataset: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      await ragTesterClient.deleteDataset(id);
      await get().fetchDatasets(); // Refresh list
      set({ isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete dataset",
        isLoading: false,
      });
      throw error;
    }
  },

  // Evaluation actions
  submitEvaluation: async (params: EvaluationRequest) => {
    set({ isLoading: true, error: null });
    try {
      const response = await ragTesterClient.submitEvaluation(params);
      const job: EvaluationJob = {
        job_id: response.job_id,
        dataset_id: params.dataset_id,
        retrieval_method: params.retrieval_method,
        k_values: params.k_values,
        status: "queued",
        created_at: response.created_at,
      };
      set((state) => ({
        jobs: [job, ...state.jobs],
        isLoading: false,
      }));
      return response.job_id;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to submit evaluation",
        isLoading: false,
      });
      throw error;
    }
  },

  fetchJob: async (jobId: string) => {
    try {
      const job = await ragTesterClient.getJobStatus(jobId);
      set((state) => ({
        jobs: state.jobs.map((j) => (j.job_id === jobId ? job : j)),
      }));
    } catch (error) {
      console.error("Failed to fetch job:", error);
    }
  },

  fetchResults: async (jobId: string) => {
    set({ isLoading: true, error: null });
    try {
      const results = await ragTesterClient.getJobResults(jobId);
      set({ currentResults: results, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch results",
        isLoading: false,
      });
    }
  },

  fetchJobs: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await ragTesterClient.listJobs();
      set({ jobs: response.jobs, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch jobs",
        isLoading: false,
      });
    }
  },

  startPolling: (jobId: string, intervalMs = 2000) => {
    const { pollingIntervals, fetchJob, stopPolling, fetchResults } = get();

    // Don't start if already polling
    if (pollingIntervals.has(jobId)) {
      return;
    }

    const intervalId = setInterval(async () => {
      try {
        const job = await ragTesterClient.getJobStatus(jobId);
        set((state) => ({
          jobs: state.jobs.map((j) => (j.job_id === jobId ? job : j)),
        }));

        // Stop polling if job is completed or failed
        if (job.status === "completed" || job.status === "failed") {
          stopPolling(jobId);

          // Auto-fetch results if completed
          if (job.status === "completed") {
            await fetchResults(jobId);
          }
        }
      } catch (error) {
        console.error("Polling error:", error);
        stopPolling(jobId);
      }
    }, intervalMs);

    set((state) => ({
      pollingIntervals: new Map(state.pollingIntervals).set(jobId, intervalId),
    }));
  },

  stopPolling: (jobId: string) => {
    const { pollingIntervals } = get();
    const intervalId = pollingIntervals.get(jobId);

    if (intervalId) {
      clearInterval(intervalId);
      const newIntervals = new Map(pollingIntervals);
      newIntervals.delete(jobId);
      set({ pollingIntervals: newIntervals });
    }
  },

  stopAllPolling: () => {
    const { pollingIntervals } = get();
    pollingIntervals.forEach((intervalId) => clearInterval(intervalId));
    set({ pollingIntervals: new Map() });
  },

  // Utilities
  setError: (error: string | null) => set({ error }),

  reset: () => {
    get().stopAllPolling();
    set({
      datasets: [],
      currentDataset: null,
      jobs: [],
      currentResults: null,
      isLoading: false,
      error: null,
      pollingIntervals: new Map(),
    });
  },
}));
