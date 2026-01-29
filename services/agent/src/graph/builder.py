"""
LangGraph graph construction and application singleton.

Builds the RAG workflow graph with all nodes and edges.
"""

import asyncio
import logging
from functools import partial

import httpx
from langgraph.graph import END, START, StateGraph
from psycopg_pool import AsyncConnectionPool

from src.graph.checkpointer import PooledAsyncPostgresSaver
from src.graph.nodes import (
    documents_handler,
    generate_queries,
    respond_simple,
    respond_with_docs,
    retrieve_documents,
    retrieve_in_parallel,
    route_query,
    route_query_condition,
)
from src.graph.state import AgentState
from src.services.core_client import CoreClient

logger = logging.getLogger(__name__)

# Global singleton
_app = None
_lock = asyncio.Lock()


async def build_graph(
    pool: AsyncConnectionPool,
    httpx_client: httpx.AsyncClient,
):
    """
    Build the LangGraph RAG workflow.

    Args:
        pool: PostgreSQL connection pool for checkpointer
        httpx_client: httpx client for Core API calls

    Returns:
        Compiled LangGraph application
    """
    # Create Core client
    core_client = CoreClient(httpx_client)

    # Create checkpointer
    checkpointer = PooledAsyncPostgresSaver(pool)

    # Create node functions with core_client injection
    async def route_query_node(state: AgentState) -> dict:
        return await route_query(state, core_client)

    async def respond_simple_node(state: AgentState) -> dict:
        return await respond_simple(state, core_client)

    async def generate_queries_node(state: AgentState) -> dict:
        return await generate_queries(state, core_client)

    async def documents_handler_node(state: AgentState) -> dict:
        return await documents_handler(state, core_client)

    async def respond_with_docs_node(state: AgentState) -> dict:
        return await respond_with_docs(state, core_client)

    # Build graph
    graph_builder = StateGraph(AgentState)

    # Add all nodes
    graph_builder.add_node("route_query", route_query_node)
    graph_builder.add_node("respond_simple", respond_simple_node)
    graph_builder.add_node("generate_queries", generate_queries_node)
    graph_builder.add_node("retrieve_in_parallel", retrieve_in_parallel)
    graph_builder.add_node("retrieve_documents", retrieve_documents)
    graph_builder.add_node("documents_handler", documents_handler_node)
    graph_builder.add_node("respond_with_docs", respond_with_docs_node)

    # Define graph flow
    graph_builder.add_edge(START, "route_query")

    # Conditional routing based on query classification
    graph_builder.add_conditional_edges(
        "route_query",
        route_query_condition,
        {
            "retrieval_required": "generate_queries",
            "just_respond": "respond_simple",
        },
    )

    # Simple response path (direct to end)
    graph_builder.add_edge("respond_simple", END)

    # Complex RAG path (parallel retrieval → processing → response)
    graph_builder.add_conditional_edges(
        "generate_queries",
        retrieve_in_parallel,
        path_map=["retrieve_documents"],
    )
    graph_builder.add_edge("retrieve_documents", "documents_handler")
    graph_builder.add_edge("documents_handler", "respond_with_docs")
    graph_builder.add_edge("respond_with_docs", END)

    # Compile with PostgreSQL persistence
    app = graph_builder.compile(checkpointer=checkpointer)
    logger.info("LangGraph application compiled successfully")

    return app


async def get_app(
    pool: AsyncConnectionPool,
    httpx_client: httpx.AsyncClient,
):
    """
    Get or create the LangGraph application singleton.

    Uses double-checked locking for thread safety.

    Args:
        pool: PostgreSQL connection pool
        httpx_client: httpx client for Core API calls

    Returns:
        Compiled LangGraph application
    """
    global _app

    if _app is None:
        async with _lock:
            if _app is None:
                _app = await build_graph(pool, httpx_client)

    return _app


def reset_app():
    """Reset the singleton (for testing)."""
    global _app
    _app = None
