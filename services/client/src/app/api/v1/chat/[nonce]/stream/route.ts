/**
 * Streaming proxy for Agent SSE endpoint.
 *
 * Next.js rewrites buffer responses, breaking SSE streaming.
 * This route handler uses Web Streams API to properly forward
 * the SSE stream from Agent to the client without buffering.
 */

const AGENT_URL = process.env.AGENT_SERVICE_URL || 'http://localhost:8001';

export async function POST(
  request: Request,
  { params }: { params: Promise<{ nonce: string }> }
) {
  const { nonce } = await params;
  const body = await request.text();

  const agentResponse = await fetch(`${AGENT_URL}/api/v1/chat/${nonce}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    body,
  });

  if (!agentResponse.ok) {
    const errorText = await agentResponse.text();
    return new Response(errorText, {
      status: agentResponse.status,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // Forward the SSE stream directly using Web Streams API (no buffering)
  return new Response(agentResponse.body, {
    status: 200,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
