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
from scraper.models import AllowedAuthor, AllowedCategory, NaverCafeData

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
    Only retrieve posts from allowed authors and categories.

    Returns:
        List of Documents
    """
    try:
        # Get allowed authors
        allowed_authors = list(
            AllowedAuthor.objects.filter(is_active=True).values_list("name", flat=True)
        )

        # Get allowed categories
        allowed_categories = list(
            AllowedCategory.objects.filter(is_active=True).values_list(
                "name", flat=True
            )
        )

        # Query posts from allowed authors and categories (removed vectorized=False check)
        posts = NaverCafeData.objects.filter(
            author__in=allowed_authors, category__in=allowed_categories
        )

        logger.info(
            f"Loaded {posts.count()} posts matching allowed authors/categories from database"
        )

        documents = []
        for post in posts:
            # Only use the content for the document text, title is in metadata
            text = post.content

            # Create document with metadata
            doc = Document(
                page_content=text,
                metadata={
                    "post_id": post.post_id,  # Keep original post_id
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
    Load posts from database, split into chunks, check existence in Pinecone,
    and ingest only new chunks using chunk_id as the vector ID.
    """
    PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
    PINECONE_ENVIRONMENT = os.environ["PINECONE_ENVIRONMENT"]
    PINECONE_INDEX_NAME = os.environ["PINECONE_INDEX_NAME"]

    # Create text splitter optimized for Korean content
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000,
        chunk_overlap=200,
        separators=["\\n\\n", "\\n", ". ", ".", "? ", "! ", "？", "！", " ", ""],
        keep_separator=False,
    )

    # Get embedding model
    embedding = get_embeddings_model()

    # Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = None  # Initialize index variable

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
        # Wait for index readiness if needed, depends on Pinecone client behavior
        # time.sleep(10) # Example: Simple wait, adjust as needed

    # Assign the index object
    index = pc.Index(PINECONE_INDEX_NAME)

    # Load posts
    raw_docs = load_posts_from_database()

    if not raw_docs:
        logger.info(
            "No documents found matching criteria in database. Nothing to ingest."
        )
        return

    logger.info(
        f"Loaded {len(raw_docs)} documents from database to check for ingestion."
    )

    # Generate chunks with unique IDs
    all_chunks = []
    chunk_ids_generated = set()  # To track unique chunk IDs within this run

    for doc in raw_docs:
        try:
            post_id = doc.metadata.get("post_id")
            if post_id is None:
                logger.warning(
                    f"Skipping document due to missing 'post_id' in metadata: {doc.metadata}"
                )
                continue

            # Create a temporary document with the content for chunking
            temp_doc = Document(
                page_content=doc.page_content, metadata=doc.metadata.copy()
            )

            # Split the content into chunks
            content_chunks = text_splitter.split_documents([temp_doc])

            # Add chunk_id to metadata for each chunk
            for i, chunk in enumerate(content_chunks):
                chunk_id = f"{post_id}_{i}"
                # Ensure chunk_id is unique within this run before adding
                if chunk_id not in chunk_ids_generated:
                    chunk.metadata["chunk_id"] = chunk_id
                    chunk.metadata["text"] = (
                        chunk.page_content
                    )  # Add 'text' key for Pinecone mapping
                    all_chunks.append(chunk)
                    chunk_ids_generated.add(chunk_id)
                else:
                    logger.warning(
                        f"Duplicate chunk_id '{chunk_id}' generated for post {post_id}. Skipping."
                    )

        except Exception as e:
            logger.error(
                f"Error processing document for post_id {doc.metadata.get('post_id', 'N/A')}: {e}",
                exc_info=True,
            )

    if not all_chunks:
        logger.info("No valid chunks generated after splitting documents.")
        return

    logger.info(f"Generated {len(all_chunks)} potential chunks for ingestion.")

    # Check which chunk IDs already exist in Pinecone
    chunk_ids_to_check = [chunk.metadata["chunk_id"] for chunk in all_chunks]
    existing_ids = set()
    try:
        # Fetch in batches if necessary (Pinecone fetch limit might be 1000)
        batch_size = 1000
        for i in range(0, len(chunk_ids_to_check), batch_size):
            batch_ids = chunk_ids_to_check[i : i + batch_size]
            logger.info(
                f"Checking existence of {len(batch_ids)} chunk IDs in Pinecone (batch {i//batch_size + 1})..."
            )
            fetch_response = index.fetch(ids=batch_ids)
            existing_ids.update(fetch_response.vectors.keys())
        logger.info(f"Found {len(existing_ids)} existing chunk IDs in Pinecone.")
    except Exception as e:
        logger.error(
            f"Error fetching existing IDs from Pinecone: {e}. Assuming all chunks are new.",
            exc_info=True,
        )
        # Decide on behavior: either stop, or proceed assuming no chunks exist (might lead to duplicates if fetch fails repeatedly)
        # For now, we'll proceed cautiously and ingest nothing if fetch fails.
        # To be robust, could implement retries or ingest all and let Pinecone handle potential conflicts if IDs match.
        # For this implementation, we will stop if fetch fails.
        logger.error("Aborting ingestion due to Pinecone fetch error.")
        return

    # Filter out chunks that already exist
    new_chunks = [
        chunk for chunk in all_chunks if chunk.metadata["chunk_id"] not in existing_ids
    ]

    if not new_chunks:
        logger.info("No new document chunks to ingest.")
    else:
        logger.info(f"Preparing to ingest {len(new_chunks)} new document chunks.")

        # Ingest only the new chunks using LangchainPinecone helper
        try:
            vectorstore = LangchainPinecone(
                index=index, embedding=embedding, text_key="text"
            )  # Use text_key='text'
            vectorstore.add_documents(
                documents=new_chunks,
                ids=[chunk.metadata["chunk_id"] for chunk in new_chunks],
            )
            logger.info(
                f"Successfully added {len(new_chunks)} new document chunks to Pinecone."
            )
        except Exception as e:
            logger.error(f"Error adding documents to Pinecone: {e}", exc_info=True)

    # Get final stats from Pinecone
    try:
        stats = index.describe_index_stats()
        logger.info(
            f"Pinecone index '{PINECONE_INDEX_NAME}' now has {stats.total_vector_count} total vectors."
        )
    except Exception as e:
        logger.warning(f"Could not retrieve final index stats from Pinecone: {e}")


if __name__ == "__main__":
    ingest_docs()
