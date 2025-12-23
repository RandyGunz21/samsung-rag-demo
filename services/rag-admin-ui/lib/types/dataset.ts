// Types for test datasets matching backend Pydantic models

export interface ExpectedDocument {
  doc_id: string;
  relevance: number; // 0-1 scale
}

export interface TestQuery {
  query: string;
  expected_docs: ExpectedDocument[];
}

export interface TestDatasetCreate {
  name: string;
  description?: string;
  queries: TestQuery[];
}

export interface TestDatasetUpdate {
  name?: string;
  description?: string;
  queries?: TestQuery[];
}

export interface TestDataset {
  id: string;
  name: string;
  description?: string;
  queries: TestQuery[];
  query_count: number;
  created_at: string;
  updated_at?: string;
}

export interface DatasetListItem {
  id: string;
  name: string;
  description?: string;
  query_count: number;
  created_at: string;
}

export interface DatasetListResponse {
  datasets: DatasetListItem[];
  total: number;
}
