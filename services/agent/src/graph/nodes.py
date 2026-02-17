"""
LangGraph node functions for RAG agent.

Ported from changple2/chatbot/bot.py with Django ORM calls replaced
by Core REST API calls via CoreClient.
"""

import logging
import re
from typing import Any, Literal, TypedDict, Union, cast

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, AnyMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.constants import Send
from pydantic import BaseModel

from src.config import get_settings
from src.graph.memory import get_context_messages
from src.graph.prompts import (
    DOC_RELEVANCE_PROMPT_TEMPLATE,
    GENERATE_QUERIES_PROMPT_TEMPLATE,
    RAG_RESPONSE_PROMPT,
    ROUTER_SYSTEM_PROMPT,
    SIMPLE_RESPONSE_PROMPT,
    USER_ATTACHED_CONTENT_NOTICE,
)
from src.graph.state import AgentState, QueryState, Router
from src.services.core_client import CoreClient
from src.services.vectorstore import get_vector_store_retriever

logger = logging.getLogger(__name__)


def load_llm(
    model_name: str | None = None,
    temperature: float = 0,
    streaming: bool = False,
) -> ChatGoogleGenerativeAI:
    """
    Create and configure a Google Generative AI language model.

    Args:
        model_name: The Gemini model to use (defaults to settings)
        temperature: Randomness in generation (0-1)
        streaming: Whether to enable streaming responses

    Returns:
        Configured ChatGoogleGenerativeAI instance
    """
    settings = get_settings()

    return ChatGoogleGenerativeAI(
        model=model_name or settings.default_model,
        temperature=temperature,
        disable_streaming=not streaming,
        google_api_key=settings.google_api_key,
    )


def format_docs(docs: list[Document] | None) -> str:
    """
    Format a list of documents into a structured string for LLM consumption.

    Args:
        docs: List of Document objects to format

    Returns:
        Formatted string with document content, metadata, and URLs
    """
    if not docs:
        return "<documents></documents>"

    serialized = "\n\n".join(
        f"{i + 1}\nURL: {doc.metadata.get('source', '')}\nTitle: {doc.metadata.get('title', '')}\nContent: {doc.page_content}"
        for i, doc in enumerate(docs)
    )
    return f"""
<documents>
{serialized}
</documents>
"""


# =============================================================================
# Node Functions
# =============================================================================


async def route_query(state: AgentState, core_client: CoreClient) -> dict:
    """
    Route user queries to either simple response or complex RAG pipeline.

    Uses an LLM to classify whether the user's query requires document retrieval
    and detailed research, or can be answered with a simple response.

    Args:
        state: Current agent state with user messages
        core_client: CoreClient instance for API calls (unused in this node)

    Returns:
        Updated state with routing decision and cleaned document list
    """
    model = load_llm(model_name="gemini-2.5-flash")
    model = model.with_structured_output(Router)

    context_messages = get_context_messages(state["messages"])
    prompt = [SystemMessage(content=ROUTER_SYSTEM_PROMPT)] + context_messages

    response = cast(Router, await model.ainvoke(prompt))
    return {
        "router": response,
        "documents": "delete",  # Clear any existing documents
        "query": state["messages"][-1].content,
        "helpful_documents": [],
    }


def route_query_condition(
    state: Union[list[AnyMessage], dict[str, Any], BaseModel],
    messages_key: str = "messages",
) -> Literal["retrieval_required", "just_respond"]:
    """
    Conditional edge function for routing based on query classification.

    Args:
        state: Current agent state
        messages_key: Key for messages in state (unused but required by LangGraph)

    Returns:
        Route destination based on router classification
    """
    router = state.get("router")
    if isinstance(router, Router):
        return router.type
    elif isinstance(router, dict):
        return router.get("type", "retrieval_required")
    return "retrieval_required"


async def respond_simple(state: AgentState, core_client: CoreClient) -> dict:
    """
    Generate simple streaming responses for basic queries.

    This node handles simple greetings, exclamations, and basic questions
    that don't require document retrieval.

    Args:
        state: Current agent state
        core_client: CoreClient instance (unused in this node)

    Returns:
        State update with streaming response and answer
    """
    llm = load_llm(model_name="gemini-2.5-flash", streaming=True)

    context_messages = get_context_messages(state["messages"])
    prompt = [SystemMessage(content=SIMPLE_RESPONSE_PROMPT)] + context_messages

    # Streaming implementation for real-time response
    chunks = []
    async for chunk in llm.astream(prompt):
        chunks.append(chunk)

    # Combine all chunks into final response
    full_response = AIMessage(content="")
    if chunks:
        for chunk in chunks:
            full_response.content += chunk.content
            if not full_response.id:
                full_response.id = chunk.id

    return {"messages": [full_response], "answer": full_response.content}


async def generate_queries(state: AgentState, core_client: CoreClient) -> dict:
    """
    Generate multiple search queries for parallel document retrieval.

    Takes the user's question and creates 2-5 different search query variations
    to maximize document retrieval coverage. Includes brand information for
    better query context.

    Args:
        state: Current agent state with user query
        core_client: CoreClient for fetching brands and authors

    Returns:
        State update with search queries and allowed authors list
    """

    class QueryResponse(TypedDict):
        maximum_five_queries: list[str]

    model = load_llm(model_name="gemini-2.5-flash", temperature=1)
    model = model.with_structured_output(QueryResponse)

    # Fetch brand information via Core API
    goodto_know_brands = await core_client.get_brands_formatted()
    prompt_content = GENERATE_QUERIES_PROMPT_TEMPLATE.format(goodto_know_brands=goodto_know_brands)

    # Append user-attached content if it exists
    if user_attached_content := state.get("user_attached_content"):
        prompt_content += USER_ATTACHED_CONTENT_NOTICE.format(
            user_attached_content=user_attached_content
        )

    prompt = [SystemMessage(content=prompt_content)] + get_context_messages(state["messages"])
    response = cast(QueryResponse, await model.ainvoke(prompt))

    # Get allowed authors via Core API
    allowed_authors = await core_client.get_allowed_authors()

    return {
        "retrieve_queries": response["maximum_five_queries"],
        "allowed_authors": allowed_authors,
    }


def retrieve_in_parallel(state: AgentState) -> list[Send]:
    """
    Set up parallel document retrieval operations.

    Creates Send objects for each search query to be processed in parallel
    by separate retrieve_documents node instances.

    Args:
        state: Current agent state with search queries and allowed authors

    Returns:
        List of Send objects for parallel execution
    """
    return [
        Send("retrieve_documents", (QueryState(query=query), state["allowed_authors"]))
        for query in state["retrieve_queries"]
    ]


async def retrieve_documents(args: tuple[QueryState, list[str]]) -> dict:
    """
    Retrieve documents from Pinecone vector store for a single query.

    This function runs in parallel for each search query, performing
    vector similarity search with author filtering.

    Args:
        args: Tuple of (QueryState, allowed_authors_list)

    Returns:
        Dictionary with retrieved documents
    """
    state, allowed_authors = args
    retriever = get_vector_store_retriever(allowed_authors)
    response = await retriever.ainvoke(state.query)
    return {"documents": response}


async def documents_handler(state: AgentState, core_client: CoreClient) -> dict:
    """
    Process retrieved documents and filter for relevance.

    Takes all retrieved documents, fetches their full content from Core API,
    and uses an LLM to determine which documents are actually relevant to
    the user's question.

    Args:
        state: Current agent state with retrieved documents
        core_client: CoreClient for fetching full post content

    Returns:
        State update with filtered, relevant documents
    """
    # Deduplicate documents by ID
    documents_ids = []
    for doc in state["documents"]:
        if doc.id not in documents_ids:
            documents_ids.append(doc.id)

    # Fetch full content for each unique document via Core API
    formatted_docs_dict = {"documents": []}
    for doc_id in documents_ids:
        post_id = int(doc_id)
        post_data = await core_client.get_post_content(post_id)

        temp_doc = Document(
            page_content=post_data.get("content", ""),
            metadata={
                "source": post_data.get("url", f"https://cafe.naver.com/cjdckddus/{post_id}"),
                "title": post_data.get("title", ""),
            },
        )
        formatted_docs_dict["documents"].append(temp_doc)

    # Use LLM to filter for relevant documents
    class DocRelevance(TypedDict):
        helpful_docs: list[int]

    llm = load_llm(streaming=True)
    llm = llm.with_structured_output(DocRelevance)
    temp_docs = format_docs(formatted_docs_dict["documents"])

    system_prompt = DOC_RELEVANCE_PROMPT_TEMPLATE.format(
        doc_count=len(formatted_docs_dict["documents"])
    )

    # Add user_attached_content to the prompt if it exists
    if user_attached_content := state.get("user_attached_content"):
        truncated_content = (
            user_attached_content[:1000] + "..."
            if len(user_attached_content) > 1000
            else user_attached_content
        )
        system_prompt += f"""

**지시 표현(deixis)**: 사용자의 질문중 '이것', '이 글', '이 내용', '여기' 등과 같이 대상을 가리키는 말이 있다면 'user_attached_content'를 참조하여 무엇을 지칭하는 것인지 파악하세요.

<user_attached_content>
{truncated_content}
</user_attached_content>
"""

    system_prompt += f"""

{temp_docs}

만약 유저의 질문에 답변하는데 도움이 되는 문서가 없다면 빈 리스트를 Return하세요.
"""

    messages = [{"role": "system", "content": system_prompt}] + get_context_messages(
        state["messages"]
    )
    response = cast(DocRelevance, await llm.ainvoke(messages))

    # Filter documents based on LLM relevance assessment
    filtered_docs = []
    filtered_helpful_docs = []

    if len(response["helpful_docs"]) > 0:
        for idx in response["helpful_docs"]:
            if 1 <= idx <= len(formatted_docs_dict["documents"]):
                filtered_docs.append(formatted_docs_dict["documents"][int(idx - 1)])
                filtered_helpful_docs.append(len(filtered_docs))
        filtered_docs_dict = {"documents": filtered_docs}
    else:
        filtered_docs_dict = {"documents": []}

    return {"documents": filtered_docs_dict, "helpful_documents": filtered_helpful_docs}


async def respond_with_docs(state: AgentState, core_client: CoreClient) -> dict:
    """
    Generate comprehensive streaming responses using retrieved documents.

    This is the main RAG response node that takes filtered, relevant documents
    and generates a detailed answer based on the Changple knowledge base.

    Args:
        state: Current agent state with relevant documents
        core_client: CoreClient instance (unused in this node)

    Returns:
        State update with streaming RAG response and answer
    """
    llm = load_llm(streaming=True)

    # Format retrieved documents
    retrieved_docs_context = format_docs(state["documents"])

    # Get user-attached content
    user_attached_context = state.get("user_attached_content")

    # Combine contexts
    final_context = f"""
{retrieved_docs_context}
"""

    if user_attached_context:
        final_context += f"""
<user_attached_content>
{user_attached_context}
</user_attached_content>

**지시 표현(deixis)**: 사용자의 질문중 '이것', '이 글', '이 내용', '여기' 등과 같이 대상을 가리키는 말이 있다면 'user_attached_content'를 참조하여 무엇을 지칭하는 것인지 파악하세요.
"""

    prompt = RAG_RESPONSE_PROMPT.format(context=final_context)
    messages = [{"role": "system", "content": prompt}] + get_context_messages(state["messages"])

    # Streaming implementation for real-time RAG response
    chunks = []
    async for chunk in llm.astream(messages):
        chunks.append(chunk)

    # Combine all chunks into final response
    full_response = AIMessage(content="")
    if chunks:
        for chunk in chunks:
            full_response.content += chunk.content
            if not full_response.id:
                full_response.id = chunk.id

    # Generate source documents info from helpful_documents (indices) and documents
    source_documents = []
    source_url_mapping = {}

    if state.get("helpful_documents") and state.get("documents"):
        documents = state["documents"]
        for doc_index in state["helpful_documents"]:
            try:
                doc_index_int = int(float(doc_index))
                actual_index = doc_index_int - 1
                if 0 <= actual_index < len(documents):
                    doc = documents[actual_index]
                    source_url = doc.metadata.get("source", "")
                    if "cafe.naver.com/cjdckddus/" in source_url:
                        post_id = source_url.split("/")[-1]
                        source_documents.append(
                            {
                                "id": int(post_id),
                                "title": doc.metadata.get("title", ""),
                                "source": source_url,
                            }
                        )
                        source_url_mapping[doc_index_int] = source_url
            except (ValueError, IndexError):
                continue

    # Replace citation numbers with clickable markdown links
    processed_content = full_response.content

    def replace_citation(match):
        citation_num = int(match.group(1))
        if citation_num in source_url_mapping:
            return f"[\\[{citation_num}\\]]({source_url_mapping[citation_num]})"
        return match.group(0)

    processed_content = re.sub(r"\[(\d+)\]", replace_citation, processed_content)
    full_response.content = processed_content

    return {
        "messages": [full_response],
        "answer": full_response.content,
        "source_documents": source_documents,
    }


# =============================================================================
# Node Wrappers for Graph Builder
# =============================================================================

# These are created in builder.py with core_client injection
