"""
Pinecone vector store setup for document retrieval.
"""

import logging

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from src.config import get_settings

logger = logging.getLogger(__name__)


def load_embeddings() -> OpenAIEmbeddings:
    """
    Create and configure OpenAI embeddings for vector store operations.

    Returns:
        Configured OpenAIEmbeddings instance
    """
    settings = get_settings()

    return OpenAIEmbeddings(
        model=settings.embedding_model,
        chunk_size=200,
        api_key=settings.openai_api_key,
    )


def get_vector_store() -> PineconeVectorStore:
    """
    Get Pinecone vector store instance.

    Returns:
        Configured PineconeVectorStore
    """
    settings = get_settings()

    return PineconeVectorStore(
        index_name=settings.pinecone_index_name,
        embedding=load_embeddings(),
        text_key="text",
        pinecone_api_key=settings.pinecone_api_key,
    )


def get_vector_store_retriever(allowed_authors: list[str], k: int = 4):
    """
    Create a Pinecone vector store retriever with author-based filtering.

    Args:
        allowed_authors: List of author names to include in search results
        k: Number of documents to retrieve

    Returns:
        Configured Pinecone retriever with author filtering
    """
    vector_store = get_vector_store()

    return vector_store.as_retriever(
        search_kwargs={
            "k": k,
            "filter": {"author": {"$in": allowed_authors}},
        }
    )
