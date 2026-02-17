"""
Memory management for LangGraph conversations.

Implements sliding window with summarization to prevent unbounded
message growth while preserving conversation context.
"""

import logging

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import get_settings

logger = logging.getLogger(__name__)

# Memory constants
CONTEXT_WINDOW_SIZE = 5  # Number of recent messages to include in LLM context
WINDOW_SIZE = 10  # Number of recent messages to keep after compaction
SUMMARIZE_THRESHOLD = 20  # Trigger summarization when total messages exceed this
SUMMARY_PREFIX = "[대화 요약] "

SUMMARIZE_PROMPT = """아래 대화 내용을 간결하게 요약해주세요.
핵심 질문, 답변, 주요 정보를 빠짐없이 포함하되 500자 이내로 작성하세요.
요약은 한국어로 작성하세요.

대화 내용:
{conversation}"""


def get_context_messages(
    messages: list[BaseMessage],
    context_size: int = CONTEXT_WINDOW_SIZE,
) -> list[BaseMessage]:
    """
    Get recent messages for LLM context window.

    If there's a summary message (SystemMessage with SUMMARY_PREFIX), include it
    followed by the most recent messages. Otherwise just return the tail.

    Args:
        messages: Full list of messages from checkpoint
        context_size: Number of recent messages to include

    Returns:
        List of messages suitable for LLM context
    """
    if not messages:
        return []

    # Check if first message is a summary
    if (
        messages
        and isinstance(messages[0], SystemMessage)
        and messages[0].content.startswith(SUMMARY_PREFIX)
    ):
        summary = messages[0]
        recent = messages[1:][-context_size:]
        return [summary] + recent

    return messages[-context_size:]


async def summarize_messages(messages: list[BaseMessage]) -> str:
    """
    Summarize a list of messages using LLM.

    Args:
        messages: Messages to summarize

    Returns:
        Summary string prefixed with SUMMARY_PREFIX
    """
    settings = get_settings()

    conversation_text = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            conversation_text.append(f"사용자: {msg.content}")
        elif isinstance(msg, AIMessage):
            # Truncate long AI responses
            content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            conversation_text.append(f"AI: {content}")

    prompt = SUMMARIZE_PROMPT.format(conversation="\n".join(conversation_text))

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        google_api_key=settings.google_api_key,
    )

    response = await llm.ainvoke(prompt)
    return f"{SUMMARY_PREFIX}{response.content}"


async def manage_memory(messages: list[BaseMessage]) -> list[BaseMessage] | None:
    """
    Manage conversation memory with sliding window and summarization.

    When message count exceeds SUMMARIZE_THRESHOLD, summarizes older messages
    and keeps only the most recent WINDOW_SIZE messages.

    Args:
        messages: Current list of messages from checkpoint

    Returns:
        Compacted message list if summarization occurred, None otherwise
    """
    if not messages:
        return None

    # Filter to conversation messages only (skip existing summary)
    if isinstance(messages[0], SystemMessage) and messages[0].content.startswith(SUMMARY_PREFIX):
        conversation_messages = messages[1:]
        existing_summary = messages[0].content
    else:
        conversation_messages = messages
        existing_summary = None

    # Check if compaction is needed
    if len(conversation_messages) <= SUMMARIZE_THRESHOLD:
        return None

    # Split: messages to summarize vs messages to keep
    to_summarize = conversation_messages[:-WINDOW_SIZE]
    to_keep = conversation_messages[-WINDOW_SIZE:]

    # If there was an existing summary, include it in summarization context
    if existing_summary:
        summary_context = [SystemMessage(content=existing_summary)] + list(to_summarize)
    else:
        summary_context = list(to_summarize)

    try:
        summary = await summarize_messages(summary_context)
        logger.info(
            f"Memory compacted: {len(conversation_messages)} messages → "
            f"1 summary + {len(to_keep)} recent messages"
        )
        return [SystemMessage(content=summary)] + list(to_keep)
    except Exception as e:
        logger.error(f"Failed to summarize messages: {e}")
        return None
