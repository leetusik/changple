"""
SSE chat endpoints for real-time streaming.

Replaces WebSocket with POST-based SSE for simpler client implementation
and better compatibility with standard HTTP infrastructure.
"""

import json
import logging
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from src.api.dependencies import Core, HttpxClient, Pool, RedisServiceDep
from src.graph.builder import get_app
from src.graph.memory import manage_memory
from src.graph.prompts import STATUS_MESSAGES
from src.schemas.chat import (
    ChatSendRequest,
    SourceDocument,
    SSEChunkData,
    SSEEndData,
    SSEErrorData,
    SSEStatusData,
    SSEStoppedData,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# Redis key for concurrent generation guard
GENERATING_KEY_PREFIX = "agent:generating:"
GENERATING_KEY_TTL = 600  # 10 minutes max

# Nodes that produce the actual response (filter out structured output from other nodes)
RESPONSE_NODES = {"respond_simple", "respond_with_docs"}


def sse_event(event: str, data: str, event_id: str | None = None) -> str:
    """Format an SSE event string."""
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {data}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


def sse_json_event(event: str, data: dict | object, event_id: str | None = None) -> str:
    """Format an SSE event with JSON data."""
    if hasattr(data, "model_dump"):
        json_str = data.model_dump_json()
    else:
        json_str = json.dumps(data, ensure_ascii=False)
    return sse_event(event, json_str, event_id)


@router.post("/{nonce}/stream")
async def send_and_stream(
    nonce: str,
    request: ChatSendRequest,
    pool: Pool,
    httpx_client: HttpxClient,
    core_client: Core,
    redis_service: RedisServiceDep,
):
    """
    Send a chat message and stream the response via SSE.

    Returns a text/event-stream with the following events:
    - status: Processing status updates
    - chunk: Streaming response text chunks
    - end: Final response with source documents
    - stopped: Generation was stopped by user
    - error: Error occurred during processing
    """
    # Validate nonce
    try:
        session_nonce = str(uuid.UUID(nonce))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session nonce")

    if not request.content.strip():
        raise HTTPException(status_code=400, detail="메시지를 입력해주세요.")

    # Check concurrent generation guard
    generating_key = f"{GENERATING_KEY_PREFIX}{session_nonce}"
    is_generating = await redis_service.client.exists(generating_key)
    if is_generating:
        raise HTTPException(status_code=409, detail="이미 응답을 생성하고 있습니다.")

    logger.info(f"[SSE] Starting stream for session={session_nonce[:8]}... content={request.content[:50]!r}")

    async def event_generator():
        event_counter = 0

        # Set concurrent generation guard
        await redis_service.client.setex(generating_key, GENERATING_KEY_TTL, "1")

        try:
            # Clear any existing stop flag
            await redis_service.clear_stop_flag(session_nonce)

            # Get user-attached content if content_ids provided
            user_attached_content = None
            if request.content_ids:
                logger.debug(f"[SSE] Fetching attached content: {request.content_ids}")
                user_attached_content = await core_client.get_content_text_formatted(
                    request.content_ids
                )

            # Get the LangGraph app
            app = await get_app(pool, httpx_client)

            # Memory management: check and compact if needed
            config = {"configurable": {"thread_id": session_nonce}}
            checkpoint = await app.checkpointer.aget(config)
            if checkpoint and checkpoint.get("channel_values", {}).get("messages"):
                existing_messages = checkpoint["channel_values"]["messages"]
                msg_count = len(existing_messages)
                logger.debug(f"[SSE] Checkpoint has {msg_count} messages")
                compacted = await manage_memory(existing_messages)
                if compacted is not None:
                    logger.info(f"[SSE] Compacted {msg_count} messages → {len(compacted)}")
                    await app.aupdate_state(config, {"messages": compacted}, as_node="__start__")

            # Prepare input
            input_data = {"messages": [HumanMessage(content=request.content)]}
            if user_attached_content:
                input_data["user_attached_content"] = user_attached_content

            # Send analyzing status
            event_counter += 1
            yield sse_json_event(
                "status", SSEStatusData(message=STATUS_MESSAGES["analyzing"]), str(event_counter)
            )

            # Stream the graph execution
            full_response = ""
            source_documents = []
            was_stopped = False

            async for event in app.astream_events(input_data, config=config, version="v2"):
                # Check for stop flag
                if await redis_service.check_stop_flag(session_nonce):
                    logger.info(f"[SSE] Generation stopped for session {session_nonce[:8]}...")
                    event_counter += 1
                    yield sse_json_event("stopped", SSEStoppedData(), str(event_counter))
                    was_stopped = True
                    break

                event_type = event.get("event")
                event_name = event.get("name", "")
                node_name = event.get("metadata", {}).get("langgraph_node", "")

                # Handle node entry for status updates
                if event_type == "on_chain_start":
                    status_key = None
                    if event_name == "generate_queries":
                        status_key = "generating_queries"
                    elif event_name == "retrieve_documents":
                        status_key = "retrieving"
                    elif event_name == "documents_handler":
                        status_key = "filtering"
                    elif event_name in RESPONSE_NODES:
                        status_key = "generating"

                    if status_key:
                        logger.debug(f"[SSE] Node started: {event_name} → status={status_key}")
                        event_counter += 1
                        yield sse_json_event(
                            "status",
                            SSEStatusData(message=STATUS_MESSAGES[status_key]),
                            str(event_counter),
                        )

                # Handle streaming chunks - ONLY from response nodes
                if event_type == "on_chat_model_stream" and node_name in RESPONSE_NODES:
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        full_response += chunk.content
                        event_counter += 1
                        yield sse_json_event(
                            "chunk",
                            SSEChunkData(content=chunk.content),
                            str(event_counter),
                        )

                # Capture source documents from final state
                if event_type == "on_chain_end" and event_name in RESPONSE_NODES:
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict):
                        source_docs = output.get("source_documents", [])
                        if source_docs:
                            source_documents = [SourceDocument(**doc) for doc in source_docs]

            if not was_stopped:
                # Send end event
                event_counter += 1
                yield sse_json_event(
                    "end",
                    SSEEndData(
                        source_documents=source_documents,
                        processed_content=full_response,
                    ),
                    str(event_counter),
                )

            logger.info(
                f"[SSE] Stream completed for session={session_nonce[:8]}... "
                f"response_len={len(full_response)} sources={len(source_documents)} stopped={was_stopped}"
            )

            # Save messages to Core service
            messages_to_save = [
                {
                    "role": "user",
                    "content": request.content,
                    "attached_content_ids": request.content_ids,
                },
                {
                    "role": "assistant",
                    "content": full_response,
                    "helpful_document_post_ids": [doc.id for doc in source_documents],
                },
            ]

            await core_client.save_messages(
                session_nonce=session_nonce,
                messages=messages_to_save,
                user_id=request.user_id,
            )

        except Exception as e:
            logger.exception(f"[SSE] Error for session={session_nonce[:8]}...: {e}")
            event_counter += 1
            yield sse_json_event(
                "error",
                SSEErrorData(message=f"처리 중 오류가 발생했습니다: {str(e)}"),
                str(event_counter),
            )

        finally:
            # Clear concurrent generation guard
            await redis_service.client.delete(generating_key)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{nonce}/stop")
async def stop_generation(
    nonce: str,
    redis_service: RedisServiceDep,
):
    """Stop generation for a session."""
    try:
        session_nonce = str(uuid.UUID(nonce))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session nonce")

    await redis_service.set_stop_flag(session_nonce)
    logger.info(f"[SSE] Stop signal sent for session={session_nonce[:8]}...")
    return {"status": "ok", "message": "Stop signal sent"}
