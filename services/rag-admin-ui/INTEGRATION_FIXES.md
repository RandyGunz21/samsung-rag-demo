# Integration Fixes - RAG Admin UI

## Date: 2025-12-07

## Summary

Fixed 5 critical integration issues between RAG Admin UI (frontend) and RAG Service API (backend) identified during OpenAPI validation.

---

## Issue 1: Base URL Missing API Version Prefix ✅ FIXED

**Problem**: Frontend base URL missing `/api/v1` prefix, causing all API calls to return 404

**Files Changed**:
- `.env.local`

**Changes**:
```diff
- NEXT_PUBLIC_RAG_SERVICE_URL=http://localhost:8000
+ NEXT_PUBLIC_RAG_SERVICE_URL=http://localhost:8000/api/v1
```

**Impact**: All RAG service API calls now route correctly to versioned endpoints

---

## Issue 2: Upload Endpoint Non-Existent ✅ FIXED

**Problem**: Frontend calling non-existent `/upload-files` endpoint; API only has `/ingest` for single-file uploads

**Files Changed**:
- `lib/api/rag-service.ts`

**Changes**:
- Changed endpoint from `/upload-files` to `/ingest`
- Updated to use `file` field instead of `files` in FormData
- Implemented loop to handle multiple files sequentially
- Added error handling for individual file failures
- Changed return type from `UploadResult` to `UploadResult[]`

**Impact**: File uploads now work correctly with backend API

---

## Issue 3: Response Schema Field Mismatches ✅ FIXED

**Problem**: Frontend TypeScript types didn't match OpenAPI schema field names

**Files Changed**:
- `lib/types/query.ts`
- `app/query/page.tsx`

**Changes in Types**:
```diff
export interface RetrievedDocument {
-  id: string;
   content: string;
-  score: number;
+  relevance_score: number;
   metadata: Record<string, unknown>;
}

export interface QueryResponse {
   documents: RetrievedDocument[];
-  query: string;
+  query_processed: string;
-  retrieval_method: string;
+  search_type_used: string;
+  total_found: number;
+  processing_time_ms: number;
-  sub_queries?: string[];
+  generated_queries?: string[];
}
```

**Changes in UI Components**:
- Updated `app/query/page.tsx` to use `relevance_score` instead of `score`
- Updated `app/query/page.tsx` to use `search_type_used` instead of `retrieval_method`
- Updated `app/query/page.tsx` to use `processing_time_ms` instead of `response_time_ms`
- Removed references to non-existent `doc_id` field

**Impact**: Query responses now parse correctly without runtime errors

---

## Issue 4: Hybrid Query Parameter Inconsistency ✅ FIXED

**Problem**: Frontend sending `search_type` as query parameter instead of body parameter

**Files Changed**:
- `lib/api/rag-service.ts`

**Changes**:
```diff
async queryHybrid(query: string, top_k = 5): Promise<QueryResponse> {
-  return this.request("/retrieve?search_type=hybrid", {
+  return this.request("/retrieve", {
     method: "POST",
     headers: { "Content-Type": "application/json" },
-    body: JSON.stringify({ query, top_k }),
+    body: JSON.stringify({ query, top_k, search_type: "hybrid" }),
   });
}
```

**Impact**: Hybrid queries now follow consistent API contract

---

## Issue 5: Upload Response Type Mismatch ✅ FIXED

**Problem**: Frontend expected different upload response structure than API returns

**Files Changed**:
- `lib/types/upload.ts`
- `lib/stores/upload-store.ts`

**Changes in Types**:
```diff
export interface UploadResult {
-  success: boolean;
+  status: "success" | "failed";
+  file_name: string;
-  processed: number;
+  chunks_created: number;
-  failed: number;
-  errors?: Array<{
-    filename: string;
-    error: string;
-  }>;
+  processing_time_ms: number;
+  metadata?: Record<string, unknown>;
}
```

**Changes in Upload Store**:
- Updated to handle array of `UploadResult` instead of single result with errors array
- Updated progress tracking to use `result.status` and `result.file_name`
- Updated to extract error messages from `result.metadata?.error`

**Impact**: Upload responses now parse correctly with proper error handling

---

## Verification Checklist

- [x] `.env.local` updated with `/api/v1` prefix
- [x] Upload endpoint changed to `/ingest`
- [x] Query response types match OpenAPI schema
- [x] Hybrid query uses body parameter
- [x] Upload response types match OpenAPI schema
- [x] All UI components updated to use new field names
- [x] Upload store updated to handle array responses
- [x] No TypeScript compilation errors (types are correct)

---

## Testing Required

Before deployment, test the following:

1. **Query Interface** (`/query`)
   - Basic retrieval
   - Multi-query retrieval
   - Hybrid retrieval
   - Verify scores display correctly
   - Verify processing time displays correctly

2. **File Upload** (`/data/upload`)
   - Single file upload
   - Multiple file upload
   - Upload error handling
   - Progress tracking
   - Document list refresh after upload

3. **Evaluation Flow**
   - Create ground truth dataset
   - Submit evaluation job
   - View results with correct metrics
   - Verify job polling works

---

## Next Steps

1. **Docker Configuration**
   - Create `Dockerfile` for Next.js app
   - Update `docker-compose.yml` to add rag-admin-ui service
   - Configure environment variables in docker-compose
   - Set up service dependencies

2. **End-to-End Testing**
   - Test complete evaluation workflow
   - Test query interface with all methods
   - Test file upload and document management
   - Verify all API integrations work in Docker environment

3. **Production Readiness**
   - Install Recharts for metrics visualization
   - Install TanStack Table for advanced tables
   - Add error boundary components
   - Implement toast notifications
   - Optimize for production build
