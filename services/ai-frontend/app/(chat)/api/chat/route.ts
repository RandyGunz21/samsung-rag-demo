import { geolocation } from "@vercel/functions";
import {
  createUIMessageStream,
  JsonToSseTransformStream,
} from "ai";
import { unstable_cache as cache } from "next/cache";
import { after } from "next/server";
import {
  createResumableStreamContext,
  type ResumableStreamContext,
} from "resumable-stream";
import type { ModelCatalog } from "tokenlens/core";
import { fetchModels } from "tokenlens/fetch";
import type { VisibilityType } from "@/components/visibility-selector";
import type { ChatModel } from "@/lib/ai/models";
import { isProductionEnvironment } from "@/lib/constants";
import {
  createStreamId,
  deleteChatById,
  getChatById,
  getMessageCountByUserId,
  getMessagesByChatId,
  saveChat,
  saveMessages,
} from "@/lib/db/queries";
import type { DBMessage } from "@/lib/db/schema";
import { ChatSDKError } from "@/lib/errors";
import type { ChatMessage } from "@/lib/types";
import { convertToUIMessages, generateUUID } from "@/lib/utils";
import { generateTitleFromUserMessage } from "../../actions";
import { type PostRequestBody, postRequestBodySchema } from "./schema";

export const maxDuration = 60;

let globalStreamContext: ResumableStreamContext | null = null;

const getTokenlensCatalog = cache(
  async (): Promise<ModelCatalog | undefined> => {
    try {
      return await fetchModels();
    } catch (err) {
      console.warn(
        "TokenLens: catalog fetch failed, using default catalog",
        err
      );
      return; // tokenlens helpers will fall back to defaultCatalog
    }
  },
  ["tokenlens-catalog"],
  { revalidate: 24 * 60 * 60 } // 24 hours
);

export function getStreamContext() {
  if (!globalStreamContext) {
    try {
      globalStreamContext = createResumableStreamContext({
        waitUntil: after,
      });
    } catch (error: any) {
      if (error.message.includes("REDIS_URL")) {
        console.log(
          " > Resumable streams are disabled due to missing REDIS_URL"
        );
      } else {
        console.error(error);
      }
    }
  }

  return globalStreamContext;
}

/**
 * Fetch streaming chat response from RAG Agent Service
 */
async function streamFromAgentService(
  message: string,
  sessionId?: string
): Promise<ReadableStream> {
  const agentServiceUrl = process.env.RAG_BACKEND_URL || 'http://agent-service:8001';
  const endpoint = `${agentServiceUrl}/api/v1/chat/stream`;

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      options: {
        show_sources: true,
        similarity_threshold: 0.5,
        max_sources: 4,
      },
    }),
  });

  if (!response.ok) {
    throw new Error(`Agent service returned ${response.status}: ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error('No response body from agent service');
  }

  return response.body;
}

/**
 * Parse SSE stream from agent service and convert to UI message format
 */
function transformAgentStreamToUIStream(agentStream: ReadableStream) {
  return new ReadableStream({
    async start(controller) {
      const reader = agentStream.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let messageId = generateUUID();
      let currentText = '';
      let sources: any[] = [];
      let classification: string | null = null;

      try {
        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.trim() || line.startsWith(':')) continue;

            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                switch (data.type) {
                  case 'token':
                    currentText += data.content;
                    // Send text delta
                    controller.enqueue({
                      type: 'text-delta',
                      textDelta: data.content,
                    });
                    break;

                  case 'classification':
                    classification = data.classification;
                    break;

                  case 'sources':
                    sources = data.sources || [];
                    // Send sources as annotation
                    controller.enqueue({
                      type: 'data',
                      data: {
                        sources: sources.map((s: any) => ({
                          title: s.metadata?.source || 'Document',
                          url: s.metadata?.source || '#',
                          content: s.content,
                          relevance_score: s.relevance_score,
                          page: s.metadata?.page,
                          chunk_index: s.metadata?.chunk_index,
                        })),
                        num_sources: sources.length,
                      },
                    });
                    break;

                  case 'done':
                    // Send finish event
                    controller.enqueue({
                      type: 'finish',
                      finishReason: 'stop',
                      usage: {
                        promptTokens: 0,
                        completionTokens: 0,
                        totalTokens: 0,
                      },
                    });
                    break;
                }
              } catch (parseError) {
                console.warn('Failed to parse SSE data:', line, parseError);
              }
            }
          }
        }

        controller.close();
      } catch (error) {
        controller.error(error);
      } finally {
        reader.releaseLock();
      }
    },
  });
}

export async function POST(request: Request) {
  let requestBody: PostRequestBody;

  try {
    const json = await request.json();
    requestBody = postRequestBodySchema.parse(json);
  } catch (_) {
    return new ChatSDKError("bad_request:api").toResponse();
  }

  try {
    const {
      id,
      message,
      selectedChatModel,
      selectedVisibilityType,
    }: {
      id: string;
      message: ChatMessage;
      selectedChatModel: ChatModel["id"];
      selectedVisibilityType: VisibilityType;
    } = requestBody;

    // No authentication required - all users can access
    const anonymousUserId = "00000000-0000-0000-0000-000000000000";

    const chat = await getChatById({ id });
    let messagesFromDb: DBMessage[] = [];

    if (chat) {
      // All users can access any chat
      messagesFromDb = await getMessagesByChatId({ id });
    } else {
      const title = await generateTitleFromUserMessage({
        message,
      });

      await saveChat({
        id,
        userId: anonymousUserId,
        title,
        visibility: selectedVisibilityType,
      });
      // New chat - no need to fetch messages, it's empty
    }

    const uiMessages = [...convertToUIMessages(messagesFromDb), message];

    // Extract text content from message parts
    const userMessageText = message.parts
      .filter((part) => part.type === 'text')
      .map((part) => part.text)
      .join('\n');

    await saveMessages({
      messages: [
        {
          chatId: id,
          id: message.id,
          role: "user",
          parts: message.parts,
          attachments: [],
          createdAt: new Date(),
        },
      ],
    });

    const streamId = generateUUID();
    await createStreamId({ streamId, chatId: id });

    // Create UI message stream connected to RAG agent service
    const stream = createUIMessageStream({
      execute: async ({ writer: dataStream }) => {
        try {
          // Get streaming response from agent service
          const agentStream = await streamFromAgentService(userMessageText, id);

          // Transform agent SSE stream to UI message stream
          const uiStream = transformAgentStreamToUIStream(agentStream);

          // Pipe to data stream
          const reader = uiStream.getReader();
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            dataStream.write(value);
          }
        } catch (error) {
          console.error('Error streaming from agent service:', error);
          throw error;
        }
      },
      generateId: generateUUID,
      onFinish: async ({ messages }) => {
        await saveMessages({
          messages: messages.map((currentMessage) => ({
            id: currentMessage.id,
            role: currentMessage.role,
            parts: currentMessage.parts,
            createdAt: new Date(),
            attachments: [],
            chatId: id,
          })),
        });
      },
      onError: () => {
        return "Oops, an error occurred connecting to the RAG service!";
      },
    });

    return new Response(stream.pipeThrough(new JsonToSseTransformStream()));
  } catch (error) {
    const vercelId = request.headers.get("x-vercel-id");

    if (error instanceof ChatSDKError) {
      return error.toResponse();
    }

    console.error("Unhandled error in chat API:", error, { vercelId });
    return new ChatSDKError("offline:chat").toResponse();
  }
}

export async function DELETE(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");

  if (!id) {
    return new ChatSDKError("bad_request:api").toResponse();
  }

  // No authentication required - all users can delete any chat
  const deletedChat = await deleteChatById({ id });

  return Response.json(deletedChat, { status: 200 });
}
