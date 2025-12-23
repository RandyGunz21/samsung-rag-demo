import type { NextRequest } from "next/server";
import { deleteAllChatsByUserId, getChatsByUserId } from "@/lib/db/queries";
import { ChatSDKError } from "@/lib/errors";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;

  const limit = Number.parseInt(searchParams.get("limit") || "10", 10);
  const startingAfter = searchParams.get("starting_after");
  const endingBefore = searchParams.get("ending_before");

  if (startingAfter && endingBefore) {
    return new ChatSDKError(
      "bad_request:api",
      "Only one of starting_after or ending_before can be provided."
    ).toResponse();
  }

  // No authentication required - use anonymous user
  const anonymousUserId = "00000000-0000-0000-0000-000000000000";

  const chats = await getChatsByUserId({
    id: anonymousUserId,
    limit,
    startingAfter,
    endingBefore,
  });

  return Response.json(chats);
}

export async function DELETE() {
  // No authentication required - use anonymous user
  const anonymousUserId = "00000000-0000-0000-0000-000000000000";

  const result = await deleteAllChatsByUserId({ userId: anonymousUserId });

  return Response.json(result, { status: 200 });
}
