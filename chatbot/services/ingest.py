"""Load posts from database, clean up, split, ingest into Pinecone for RAG chatbot."""

import logging
import os
from typing import List

import django
from dotenv import load_dotenv

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Now import Django models after setting up Django
from scraper.models import AllowedAuthor, NaverCafeData

load_dotenv()

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Pinecone as LangchainPinecone
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_embeddings_model() -> Embeddings:
    """
    Returns an embedding model instance.
    The chunk_size parameter here is for API batching, not text splitting.
    """
    return OpenAIEmbeddings(model="text-embedding-3-large", chunk_size=200)


def load_posts_from_database() -> List[Document]:
    """
    Load posts from database and convert to documents.
    Only retrieve posts from allowed authors and where vectorized=False.

    Returns:
        List of Documents
    """
    try:
        # Get allowed authors
        allowed_authors = list(
            AllowedAuthor.objects.filter(is_active=True).values_list("name", flat=True)
        )

        # Query posts from allowed authors and not yet vectorized
        posts = NaverCafeData.objects.filter(
            author__in=allowed_authors, vectorized=False
        )

        logger.info(f"Loaded {posts.count()} posts from database")

        documents = []
        for post in posts:
            # Only use the content for the document text, title is in metadata
            text = post.content

            # Create document with metadata
            doc = Document(
                page_content=text,
                metadata={
                    "post_id": post.post_id,  # Keep track of post_id for later updating
                    "title": post.title or "",
                    "author": post.author or "",
                    "category": post.category or "",
                    "published_date": post.published_date or "",
                    "url": post.url or "",
                },
            )
            documents.append(doc)

        return documents
    except Exception as e:
        logger.error(f"Error loading posts from database: {e}")
        return []


def ingest_docs():
    """
    Load posts from database, split into chunks, and ingest into Pinecone.
    Only ingests posts from allowed authors and where vectorized=False.
    """
    PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
    PINECONE_ENVIRONMENT = os.environ["PINECONE_ENVIRONMENT"]
    PINECONE_INDEX_NAME = os.environ["PINECONE_INDEX_NAME"]

    # Create text splitter optimized for Korean content
    # Korean has higher semantic density per character compared to English
    # For character-based splitting, we need more characters to capture similar semantic content
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000,  # Increased for Korean content to capture semantically complete ideas
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", ".", "? ", "! ", "？", "！", " ", ""],
        keep_separator=False,
    )

    # Get embedding model
    embedding = get_embeddings_model()

    # Initialize Pinecone with new API (v6.0.0+)
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Check if index exists, create if it doesn't
    index_list = pc.list_indexes()
    if PINECONE_INDEX_NAME not in [index.name for index in index_list.indexes]:
        logger.info(f"Creating new Pinecone index: {PINECONE_INDEX_NAME}")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=3072,  # Dimension for text-embedding-3-large
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=PINECONE_ENVIRONMENT),
        )
        logger.info(f"Created new Pinecone index: {PINECONE_INDEX_NAME}")

    # Load posts
    raw_docs = load_posts_from_database()

    if not raw_docs:
        logger.error("No documents loaded from database")
        return

    logger.info(f"Loaded {len(raw_docs)} documents from database")

    # Process each document to ensure title is preserved in each chunk
    all_chunks = []
    # Keep track of post_ids and their processed chunks
    processed_post_ids = []

    # Use a transaction to ensure either all posts are updated or none
    from django.db import transaction

    try:
        with transaction.atomic():
            for doc in raw_docs:
                post_id = doc.metadata.get("post_id")
                processed_post_ids.append(post_id)

                # Create a temporary document with the content for chunking
                temp_doc = Document(
                    page_content=doc.page_content, metadata=doc.metadata
                )

                # Split the content into chunks
                content_chunks = text_splitter.split_documents([temp_doc])

                # Create unique IDs for each chunk based on post_id to avoid duplicates
                for i, chunk in enumerate(content_chunks):
                    # Add a unique ID to each chunk's metadata
                    chunk.metadata["chunk_id"] = f"{post_id}_{i}"

                # Add each chunk to the final list
                all_chunks.extend(content_chunks)

            logger.info(
                f"Split into {len(all_chunks)} chunks, each preserving the post metadata"
            )

            # Set up the Pinecone client separately to use explicit IDs
            # Create vectorstore and directly add documents with explicit IDs
            index = pc.Index(PINECONE_INDEX_NAME)

            # Batch vectors for upload
            batch_size = 100
            for i in range(0, len(all_chunks), batch_size):
                batch = all_chunks[i : i + batch_size]

                # Get embeddings for this batch
                texts = [doc.page_content for doc in batch]
                embeddings = embedding.embed_documents(texts)

                # Prepare vectors with explicit IDs
                vectors_to_upsert = []
                for j, (doc, emb) in enumerate(zip(batch, embeddings)):
                    # Use the chunk_id as the vector ID to ensure uniqueness and idempotence
                    vector_id = doc.metadata["chunk_id"]

                    # Copy metadata and add the text for retrieval
                    metadata = doc.metadata.copy()
                    metadata["text"] = doc.page_content

                    vectors_to_upsert.append(
                        {"id": vector_id, "values": emb, "metadata": metadata}
                    )

                # Upsert vectors to Pinecone
                index.upsert(vectors=vectors_to_upsert)
                logger.info(
                    f"Upserted batch {i//batch_size + 1}/{(len(all_chunks) + batch_size - 1)//batch_size}"
                )

            logger.info(
                f"Successfully added {len(all_chunks)} document chunks to Pinecone"
            )

            # Get stats from Pinecone with new API
            stats = index.describe_index_stats()
            logger.info(f"Vector store now has {stats.total_vector_count} vectors")

            # Update vectorized flag in database
            # Extract post_ids from the documents we processed
            # Update all processed posts as vectorized=True
            updated_count = NaverCafeData.objects.filter(
                post_id__in=processed_post_ids
            ).update(vectorized=True)

            logger.info(
                f"Updated vectorized flag for {updated_count} posts in database"
            )
    except Exception as e:
        logger.error(f"Transaction failed: {e}")
        # The transaction will roll back automatically
        raise


if __name__ == "__main__":
    ingest_docs()
