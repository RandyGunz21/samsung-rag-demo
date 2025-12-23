// Zustand store for upload and documents state

import { create } from "zustand";
import type {
  UploadProgress,
  Document,
  DocumentListResponse,
} from "@/lib/types";
import { ragServiceClient } from "@/lib/api";

interface UploadState {
  // Data
  uploadProgress: Record<string, UploadProgress>;
  documents: Document[];
  totalDocuments: number;
  currentPage: number;
  pageSize: number;

  // Loading states
  isLoading: boolean;
  isUploading: boolean;
  error: string | null;

  // Actions - Upload
  uploadFiles: (files: File[]) => Promise<void>;
  clearUploadProgress: () => void;

  // Actions - Documents
  fetchDocuments: (page?: number, limit?: number, search?: string) => Promise<void>;

  // Utilities
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useUploadStore = create<UploadState>((set, get) => ({
  // Initial state
  uploadProgress: {},
  documents: [],
  totalDocuments: 0,
  currentPage: 1,
  pageSize: 50,
  isLoading: false,
  isUploading: false,
  error: null,

  // Upload actions
  uploadFiles: async (files: File[]) => {
    set({ isUploading: true, error: null });

    // Initialize progress for each file
    const progress: Record<string, UploadProgress> = {};
    files.forEach((file) => {
      progress[file.name] = {
        filename: file.name,
        progress: 0,
        status: "pending",
      };
    });
    set({ uploadProgress: progress });

    try {
      // Update to uploading status
      const updatedProgress = { ...progress };
      files.forEach((file) => {
        updatedProgress[file.name] = {
          ...updatedProgress[file.name],
          status: "uploading",
        };
      });
      set({ uploadProgress: updatedProgress });

      // Upload files (returns array of results)
      const results = await ragServiceClient.uploadFiles(files);

      // Update progress based on results
      const finalProgress = { ...updatedProgress };
      results.forEach((result) => {
        const filename = result.file_name;
        if (finalProgress[filename]) {
          finalProgress[filename] = {
            ...finalProgress[filename],
            progress: 100,
            status: result.status === "success" ? "completed" : "failed",
            error: result.status === "failed" ? result.metadata?.error as string : undefined,
          };
        }
      });

      set({ uploadProgress: finalProgress, isUploading: false });

      // Refresh documents list
      await get().fetchDocuments();
    } catch (error) {
      // Mark all as failed
      const failedProgress = { ...progress };
      files.forEach((file) => {
        failedProgress[file.name] = {
          ...failedProgress[file.name],
          status: "failed",
          error: error instanceof Error ? error.message : "Upload failed",
        };
      });

      set({
        uploadProgress: failedProgress,
        isUploading: false,
        error: error instanceof Error ? error.message : "Upload failed",
      });
    }
  },

  clearUploadProgress: () => {
    set({ uploadProgress: {} });
  },

  // Documents actions
  fetchDocuments: async (page, limit, search) => {
    const currentPage = page || get().currentPage;
    const currentLimit = limit || get().pageSize;

    set({ isLoading: true, error: null });
    try {
      const response = await ragServiceClient.listDocuments(
        currentPage,
        currentLimit,
        search
      );
      set({
        documents: response.documents,
        totalDocuments: response.total,
        currentPage: response.page,
        pageSize: response.limit,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch documents",
        isLoading: false,
      });
    }
  },

  // Utilities
  setError: (error: string | null) => set({ error }),

  reset: () => {
    set({
      uploadProgress: {},
      documents: [],
      totalDocuments: 0,
      currentPage: 1,
      pageSize: 50,
      isLoading: false,
      isUploading: false,
      error: null,
    });
  },
}));
