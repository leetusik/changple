/**
 * Proxy for Agent stop generation endpoint.
 */

const AGENT_URL = process.env.AGENT_SERVICE_URL || 'http://localhost:8001';

export async function POST(
  request: Request,
  { params }: { params: Promise<{ nonce: string }> }
) {
  const { nonce } = await params;

  const agentResponse = await fetch(`${AGENT_URL}/api/v1/chat/${nonce}/stop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  const responseText = await agentResponse.text();
  return new Response(responseText, {
    status: agentResponse.status,
    headers: { 'Content-Type': 'application/json' },
  });
}
