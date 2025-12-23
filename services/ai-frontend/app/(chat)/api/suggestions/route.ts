import { getSuggestionsByDocumentId } from "@/lib/db/queries";
import { ChatSDKError } from "@/lib/errors";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const documentId = searchParams.get("documentId");

  if (!documentId) {
    return new ChatSDKError(
      "bad_request:api",
      "Parameter documentId is required."
    ).toResponse();
  }

  // No authentication required - all users can access suggestions
  const suggestions = await getSuggestionsByDocumentId({
    documentId,
  });

  if (!suggestions || suggestions.length === 0) {
    return Response.json([], { status: 200 });
  }

  return Response.json(suggestions, { status: 200 });
}
