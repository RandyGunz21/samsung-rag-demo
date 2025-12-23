# Vercel AI Chatbot → RAG Backend Integration Analysis

**Date**: 2025-12-09
**Status**: Planning Phase
**Frontend**: vercel-chatbot (fresh clone, port 3000)
**Backend**: agent-service (RAG backend, port 8001)

---

## Executive Summary

The **vercel-chatbot** (fresh clone) currently uses xAI Grok models via Vercel AI Gateway. To integrate with your custom RAG backend API, you need to:

1. **Replace the model provider** (xAI Grok → Custom RAG backend)
2. **Create an adapter** to transform backend SSE streams → Vercel AI SDK format
3. **Handle session management** (map chat IDs to session IDs)
4. **Remove unused tools** (weather, documents) since backend doesn't support them

**Complexity**: Moderate (4-6 hours implementation)
**Risk Level**: Low (pattern exists in ai-frontend)
**Recommended Approach**: **Clone adapter from ai-frontend** → Apply to vercel-chatbot

---

## Current Architecture Comparison

### Two Frontends in Your System

| Aspect | **ai-frontend** (port 3100) | **vercel-chatbot** (port 3000) |
|--------|----------------------------|-------------------------------|
| **Status** | ✅ Production, RAG-integrated | ❌ Fresh clone, NOT integrated |
| **Model** | Custom RAG backend (agent-service:8001) | xAI Grok via AI Gateway |
| **Streaming** | SSE from backend → transformed | Native Vercel AI SDK streaming |
| **Session Mgmt** | Chat ID = session_id | Chat ID (no backend mapping) |
| **Tools** | None (RAG-only) | getWeather, documents (unused) |
| **Database** | PostgreSQL (`ai_chatbot`) | PostgreSQL (`vercel_chatbot`) |
| **Purpose** | Your customized production frontend | Reference implementation for testing |

---

## Backend API Specification

### Agent Service Endpoints

**Base URL**: `http://agent-service:8001/api/v1`

#### Primary Integration Endpoint: `/chat/stream`

```http
POST /api/v1/chat/stream
Content-Type: application/json
Accept: text/event-stream
```

**Request**:
```json
{
  "message": "What is the company vacation policy?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "options": {
    "show_sources": true,
    "similarity_threshold": 0.5,
    "max_sources": 4
  }
}
```

**Response (SSE Stream)**:
```
event: start
data: {"session_id": "550e8400-...", "message_id": "msg_123456"}

event: classification
data: {"classification": "factual", "is_relevant": true}

event: token
data: {"content": "According"}

event: token
data: {"content": " to"}

event: sources
data: {"sources": [...], "num_sources": 3}

event: done
data: {"total_tokens": 156, "processing_time_ms": 2340}
```

#### Backend Response Schema

**Source Document**:
```typescript
{
  content: string;              // Document text
  metadata: {
    source: string;            // File path (e.g., "docs/policy.pdf")
    page: number;              // Page number
    chunk_index: number;       // Chunk identifier
  };
  relevance_score: number;     // 0.0 - 1.0
}
```

**Classification**: `"factual" | "conversational" | "ambiguous"`

---

## Current Vercel-Chatbot Architecture

### File: `app/(chat)/api/chat/route.ts`

**Current Flow**:
```
User Message → POST /api/chat
     ↓
streamText() with myProvider.languageModel("chat-model")
     ↓
xAI Grok API via Vercel AI Gateway
     ↓
createUIMessageStream() → Frontend
```

**Key Components**:

1. **Provider**: `lib/ai/providers.ts`
```typescript
customProvider({
  languageModels: {
    "chat-model": gateway.languageModel("xai/grok-2-vision-1212"),
    "chat-model-reasoning": gateway.languageModel("xai/grok-3-mini"),
  },
});
```

2. **Streaming**: `streamText()` from Vercel AI SDK
```typescript
const result = streamText({
  model: myProvider.languageModel(selectedChatModel),
  system: systemPrompt({ selectedChatModel, requestHints }),
  messages: convertToModelMessages(uiMessages),
  tools: {
    getWeather,
    createDocument,
    updateDocument,
    requestSuggestions,
  },
});
```

3. **Message Format**: Vercel AI SDK standard
```typescript
{
  type: 'text-delta',
  textDelta: 'token content'
}
```

---

## Integration Strategy

### Recommended Approach: **Adapter Pattern** ✅

**Clone the working implementation from `ai-frontend`** and adapt for vercel-chatbot.

### Phase 1: Create Backend API Client

**File**: `lib/api/agent-client.ts` (NEW)

```typescript
export async function streamFromAgentService(
  message: string,
  sessionId: string,
  options?: {
    show_sources?: boolean;
    similarity_threshold?: number;
    max_sources?: number;
  }
): Promise<ReadableStream> {
  const RAG_BACKEND_URL = process.env.RAG_BACKEND_URL || 'http://agent-service:8001';

  const response = await fetch(`${RAG_BACKEND_URL}/api/v1/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      options: {
        show_sources: options?.show_sources ?? true,
        similarity_threshold: options?.similarity_threshold ?? 0.5,
        max_sources: options?.max_sources ?? 4,
      },
    }),
  });

  if (!response.ok) {
    throw new Error(`Agent service returned ${response.status}`);
  }

  if (!response.body) {
    throw new Error('No response body from agent service');
  }

  return response.body;
}
```

### Phase 2: Create Stream Transformer

**File**: `lib/api/stream-transformer.ts` (NEW)

```typescript
import type { UIMessageStream } from 'ai';

export function transformAgentStreamToUIStream(
  agentStream: ReadableStream
): ReadableStream {
  const reader = agentStream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  return new ReadableStream({
    async start(controller) {
      try {
        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            controller.close();
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('event:')) {
              const eventType = line.substring(6).trim();
              continue;
            }

            if (line.startsWith('data:')) {
              const dataStr = line.substring(5).trim();
              if (!dataStr) continue;

              try {
                const data = JSON.parse(dataStr);

                switch (data.type) {
                  case 'token':
                    // Backend token → Vercel AI SDK text-delta
                    controller.enqueue({
                      type: 'text-delta',
                      textDelta: data.content,
                    });
                    break;

                  case 'start':
                    // Session initialization
                    controller.enqueue({
                      type: 'data',
                      data: {
                        session_id: data.session_id,
                        message_id: data.message_id,
                      },
                    });
                    break;

                  case 'classification':
                    // Query classification
                    controller.enqueue({
                      type: 'data',
                      data: {
                        classification: data.classification,
                        is_relevant: data.is_relevant,
                      },
                    });
                    break;

                  case 'sources':
                    // Source documents
                    controller.enqueue({
                      type: 'data',
                      data: {
                        sources: data.sources.map((s: any) => ({
                          title: extractFilename(s.metadata?.source) || 'Document',
                          content: s.content,
                          relevance_score: s.relevance_score,
                          metadata: {
                            source: s.metadata?.source,
                            page: s.metadata?.page,
                            chunk_index: s.metadata?.chunk_index,
                          },
                        })),
                        num_sources: data.num_sources,
                      },
                    });
                    break;

                  case 'done':
                    // Stream completion
                    controller.enqueue({
                      type: 'finish',
                      finishReason: 'stop',
                      usage: {
                        promptTokens: 0,  // Backend should provide these
                        completionTokens: 0,
                        totalTokens: 0,
                      },
                    });
                    break;

                  case 'error':
                    // Error handling
                    controller.error(new Error(data.error || 'Unknown error'));
                    break;
                }
              } catch (parseError) {
                console.error('Failed to parse SSE data:', dataStr, parseError);
              }
            }
          }
        }
      } catch (error) {
        controller.error(error);
      }
    },
  });
}

function extractFilename(path: string | undefined): string {
  if (!path) return 'Unknown';
  const parts = path.split('/');
  return parts[parts.length - 1].replace(/\.[^/.]+$/, '');
}
```

### Phase 3: Modify Chat Route

**File**: `app/(chat)/api/chat/route.ts` (MODIFY)

**BEFORE** (lines 180-243):
```typescript
const result = streamText({
  model: myProvider.languageModel(selectedChatModel),
  system: systemPrompt({ selectedChatModel, requestHints }),
  messages: convertToModelMessages(uiMessages),
  // ... tools, etc.
});
```

**AFTER**:
```typescript
import { streamFromAgentService } from '@/lib/api/agent-client';
import { transformAgentStreamToUIStream } from '@/lib/api/stream-transformer';

// Replace streamText() with backend API call
const agentStream = await streamFromAgentService(
  message.parts[0].text,  // User message
  id,                      // Chat ID = session ID
  {
    show_sources: true,
    similarity_threshold: 0.5,
    max_sources: 4,
  }
);

const transformedStream = transformAgentStreamToUIStream(agentStream);
```

### Phase 4: Remove Unused Components

**Files to Clean Up**:
1. ❌ `lib/ai/tools/get-weather.ts` - Backend doesn't support weather API
2. ❌ `lib/ai/tools/create-document.ts` - Not using document tools
3. ❌ `lib/ai/tools/update-document.ts` - Not using document tools
4. ❌ `lib/ai/tools/request-suggestions.ts` - Backend generates these differently
5. ⚠️ `lib/ai/providers.ts` - Keep but won't be used (fallback option)

**Reason**: Your RAG backend provides:
- ✅ Document retrieval (built-in RAG)
- ✅ Source citations
- ✅ Query classification
- ❌ Weather API (not RAG-related)
- ❌ Document creation (backend is read-only)

---

## Message Format Mapping

### Backend SSE → Vercel AI SDK

| Backend Event | Vercel AI SDK Event | Transformation |
|---------------|---------------------|----------------|
| `event: token`<br>`data: {"content": "word"}` | `{type: 'text-delta', textDelta: 'word'}` | Direct mapping |
| `event: start`<br>`data: {"session_id": "..."}` | `{type: 'data', data: {...}}` | Metadata annotation |
| `event: classification`<br>`data: {"classification": "factual"}` | `{type: 'data', data: {...}}` | Metadata annotation |
| `event: sources`<br>`data: {"sources": [...]}` | `{type: 'data', data: {...}}` | Source transformation |
| `event: done`<br>`data: {"total_tokens": 156}` | `{type: 'finish', ...}` | Stream completion |
| `event: error`<br>`data: {"error": "msg"}` | `controller.error(new Error(...))` | Error propagation |

---

## Session Management

### Current vs Required

**Current (vercel-chatbot)**:
```typescript
const chat = await getChatById({ id });  // id from request
// No backend session mapping
```

**Required Integration**:
```typescript
const chat = await getChatById({ id });
// id (chat UUID) === session_id (backend UUID)
// 1:1 direct mapping
```

**Strategy**: **Direct 1:1 mapping** (simplest approach)
- Frontend chat ID → Backend session ID
- No transformation needed
- Backend creates session if not provided

---

## Environment Variables

### Required in `docker-compose.yml`

**Current**:
```yaml
environment:
  - RAG_BACKEND_URL=http://agent-service:8001  # ✅ Already set
  - NODE_ENV=development  # ✅ Already set
```

**No additional env vars needed** - backend URL already configured.

---

## Database Consideration

### Separate Databases

- **vercel-chatbot**: `vercel_chatbot` database ✅
- **ai-frontend**: `ai_chatbot` database ✅

**No conflict** - each frontend has isolated data.

---

## Port Configuration Issues

### Current Problem: Redirect Loop

**Logs show**:
```
GET /api/auth/guest?redirectUrl=... 307 (infinite loop)
```

**Root Cause** (from previous session):
- `NODE_ENV=development` is set ✅
- But application still showing redirect loop

**Action Needed**:
1. Verify cookies are being set:
```bash
curl -sL -I http://localhost:3000/api/auth/guest | grep set-cookie
```

2. Check healthcheck status:
```bash
docker-compose ps vercel-chatbot
```

**Note**: This is SEPARATE from backend integration - must be fixed first.

---

## Implementation Checklist

### Pre-Integration (Fix Current Issues)
- [ ] Resolve authentication redirect loop (vercel-chatbot:18-20)
- [ ] Verify application loads in browser
- [ ] Confirm PostgreSQL `vercel_chatbot` database exists
- [ ] Test guest login works

### Integration Implementation
- [ ] Create `lib/api/agent-client.ts`
- [ ] Create `lib/api/stream-transformer.ts`
- [ ] Modify `app/(chat)/api/chat/route.ts`
- [ ] Remove unused tool files
- [ ] Update imports and types

### Testing
- [ ] Send test message → verify backend receives it
- [ ] Check streaming tokens appear in UI
- [ ] Verify sources display correctly
- [ ] Test session persistence across messages
- [ ] Confirm classification badges show
- [ ] Validate error handling works

### UI Enhancements (Optional)
- [ ] Add source citation display
- [ ] Show classification badges
- [ ] Display relevance scores
- [ ] Add "powered by RAG" indicator

---

## Code References from ai-frontend

### Working Implementation Location

**Full working adapter**: `/mnt/c/Users/rangunaw/Documents/rag-demo/services/ai-frontend/app/(chat)/api/chat/route.ts`

**Key sections to copy**:
- Lines 57-86: `streamFromAgentService()` function
- Lines 113-204: `transformAgentStreamToUIStream()` function
- Lines 240-290: Modified chat route integration

**Strategy**: **Copy → Adapt** (don't rewrite from scratch)

---

## Comparison: Before vs After Integration

### Before (Current)

```
User → vercel-chatbot:3000 → Vercel AI Gateway → xAI Grok API
                                    ↓
                         Response from Grok model
```

**Limitations**:
- ❌ No RAG retrieval
- ❌ No source citations
- ❌ No document search
- ✅ General conversation works

### After (Integrated)

```
User → vercel-chatbot:3000 → agent-service:8001 → RAG Service:8000
                                    ↓                      ↓
                              Ollama LLM           ChromaDB + Docs
                                    ↓
                         Response with sources
```

**Capabilities**:
- ✅ RAG-powered responses
- ✅ Source citations with relevance scores
- ✅ Document search
- ✅ Query classification
- ✅ Session-based context

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Breaking current functionality** | Low | High | Keep xAI provider as fallback |
| **SSE parsing errors** | Medium | Medium | Copy proven parser from ai-frontend |
| **Session management bugs** | Low | Low | Use 1:1 mapping (simple) |
| **Source display issues** | Medium | Low | Transform metadata properly |
| **Performance degradation** | Low | Low | Backend already handles streaming efficiently |

**Overall Risk**: **LOW** - Pattern proven in ai-frontend

---

## Timeline Estimate

| Phase | Duration | Complexity |
|-------|----------|------------|
| **Fix redirect loop** | 30 min | Low |
| **Create API client** | 1 hour | Low |
| **Create transformer** | 2 hours | Medium |
| **Modify chat route** | 1 hour | Low |
| **Testing & debugging** | 2 hours | Medium |
| **Total** | **4-6 hours** | **Moderate** |

---

## Next Steps

### Immediate Actions

1. **Fix Current Issues First**:
```bash
# Check authentication status
docker exec vercel-chatbot env | grep NODE_ENV
curl -sL -I http://localhost:3000/api/auth/guest
```

2. **Test Backend Availability**:
```bash
curl http://localhost:8001/api/v1/health
```

3. **Review ai-frontend Implementation**:
```bash
cat services/ai-frontend/app/(chat)/api/chat/route.ts | grep -A 20 "streamFromAgentService"
```

### Implementation Order

1. ✅ **Analysis Complete** (this document)
2. ⏳ **Fix redirect loop** (prerequisite)
3. ⏳ **Copy adapter from ai-frontend**
4. ⏳ **Test with single message**
5. ⏳ **Refine source display**
6. ⏳ **Production validation**

---

## Success Criteria

- [ ] User sends message → RAG backend processes it
- [ ] Streaming response displays word-by-word
- [ ] Source citations appear below response
- [ ] Classification badge shows (📚 factual / 💬 conversational)
- [ ] Session persists across multiple messages
- [ ] No errors in console or logs
- [ ] Performance comparable to ai-frontend

---

## Conclusion

**Recommendation**: **Clone the working adapter from ai-frontend** rather than implementing from scratch.

**Rationale**:
- ✅ Proven implementation exists
- ✅ Same backend API
- ✅ Same Vercel AI SDK
- ✅ Only 4-6 hours to adapt
- ✅ Low risk

**Priority**: **Fix redirect loop first**, then implement integration.

**References**:
- Backend API: `/docs/api/openapi-agent-service.yaml`
- Working Frontend: `services/ai-frontend/app/(chat)/api/chat/route.ts`
- This Analysis: `services/vercel-chatbot/INTEGRATION_ANALYSIS.md`

---

**Next Command**: Fix redirect loop → Verify authentication works → Begin integration
