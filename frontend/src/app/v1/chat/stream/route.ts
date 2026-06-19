import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND_URL =
  process.env.BACKEND_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  const auth = request.headers.get("authorization");
  const body = await request.text();

  const backendResponse = await fetch(`${BACKEND_URL}/v1/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(auth ? { Authorization: auth } : {}),
    },
    body,
  });

  if (!backendResponse.ok || !backendResponse.body) {
    const errText = await backendResponse.text();
    return new Response(errText, {
      status: backendResponse.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(backendResponse.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
