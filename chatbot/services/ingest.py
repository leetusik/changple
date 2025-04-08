"""Load posts from database, clean up, split, ingest into Pinecone for RAG chatbot."""

import logging
import os
import time  # Added for retry sleep
from typing import List

import django
from django.db.models import Q
from dotenv import load_dotenv

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Now import Django models after setting up Django
from scraper.models import NaverCafeData

load_dotenv()

import pinecone  # Use v2.x import
from langchain_community.vectorstores import Pinecone as LangchainPinecone
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import OpenAIEmbeddings

from chatbot.services.content_evaluator import evaluate_content, summary_and_keywords

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def gpt_summarize(doc: Document) -> Document:
    """
    Summarize the content of a document using GPT.
    """
    object = None
    ### notation ###
    if doc.metadata["notation"] is not None:
        pass
    else:
        doc.metadata["notation"] = evaluate_content(doc.page_content)

        # Update the notation field in the NaverCafeData record
        try:
            post_id = doc.metadata["post_id"]
            object = NaverCafeData.objects.get(post_id=post_id)
            object.notation = doc.metadata["notation"]
            object.save()
            logger.info(
                f"Updated notation for post_id {post_id} to {doc.metadata['notation']}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to update notation for post_id {doc.metadata.get('post_id')}: {e}"
            )

    ### summary ###
    doc.page_content, doc.metadata["keywords"] = summary_and_keywords(doc.page_content)
    if object:
        object.keywords = doc.metadata["keywords"]
        object.save()
    else:
        object = NaverCafeData.objects.get(post_id=doc.metadata["post_id"])
        object.keywords = doc.metadata["keywords"]
        object.save()
    return doc


def get_embeddings_model() -> Embeddings:
    """
    Returns an embedding model instance.
    The chunk_size parameter here is for API batching, not text splitting.
    """
    return OpenAIEmbeddings(model="text-embedding-3-large", chunk_size=200)


def load_posts_from_database(
    min_content_length: int = 1000,
) -> List[Document]:
    """
    Load posts from database and convert to documents.
    Only retrieve posts from allowed authors and categories.

    Returns:
        List of Documents
    """
    try:
        # Get allowed authors
        allowed_authors = [
            "창플",
        ]

        # Query posts from allowed authors and categories with content length > min_content_length
        posts = NaverCafeData.objects.filter(
            author__in=allowed_authors,
            content__len__gt=min_content_length,
        ).filter(Q(notation=None) | Q(keywords=None))

        logger.info(
            f"Loaded {posts.count()} posts matching allowed authors and content length > {min_content_length} from database"
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
                    "title": post.title,
                    "keywords": post.keywords,
                    "notation": post.notation,
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
    Uses retries for Pinecone fetch operations.
    Raises RuntimeError if ingestion fails critically (e.g., fetch after retries).
    """
    PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
    PINECONE_ENVIRONMENT = os.environ["PINECONE_ENVIRONMENT"]
    PINECONE_INDEX_NAME = os.environ["PINECONE_INDEX_NAME"]
    MAX_FETCH_RETRIES = 3
    INITIAL_BACKOFF = 2  # seconds

    # Get embedding model
    embedding = get_embeddings_model()

    # Initialize Pinecone using v2.x syntax
    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
    index = None  # Initialize index variable

    # Check if index exists, create if it doesn't using v2.x syntax
    index_list = pinecone.list_indexes()
    if PINECONE_INDEX_NAME not in index_list:
        logger.info(f"Creating new Pinecone index: {PINECONE_INDEX_NAME}")
        pinecone.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=3072,  # Dimension for text-embedding-3-large
            metric="cosine",
            # Remove ServerlessSpec, environment is handled in init
            # pod_type="p1.x1" # Example: Add pod_type if needed for v2 non-serverless
        )
        logger.info(f"Created new Pinecone index: {PINECONE_INDEX_NAME}")
        # Wait for index readiness if needed
        # time.sleep(60) # Example: Simple wait, adjust as needed

    # Assign the index object using v2.x syntax
    index = pinecone.Index(PINECONE_INDEX_NAME)

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

    existing_ids = set()
    try:
        batch_size = 25  # Reduced batch size from 100 to 25 to avoid timeouts
        for i in range(0, len(raw_docs), batch_size):
            batch_docs = raw_docs[i : i + batch_size]
            batch_ids = [doc.metadata["post_id"] for doc in batch_docs]
            logger.info(
                f"Checking existence of {len(batch_docs)} documents in Pinecone (batch {i//batch_size + 1})..."
            )

            # Retry logic for fetch
            for attempt in range(MAX_FETCH_RETRIES):
                try:
                    fetch_response = index.fetch(ids=batch_ids)
                    existing_ids.update(fetch_response.vectors.keys())
                    logger.debug(
                        f"Batch {i//batch_size + 1} fetch successful on attempt {attempt + 1}"
                    )
                    break  # Success, exit retry loop for this batch
                except Exception as fetch_e:
                    # Check if it's a server error (e.g., 5xx) potentially worth retrying
                    is_server_error = (
                        hasattr(fetch_e, "status") and fetch_e.status >= 500
                    )

                    logger.warning(
                        f"Pinecone fetch attempt {attempt + 1}/{MAX_FETCH_RETRIES} failed for batch {i//batch_size + 1}: {fetch_e}"
                    )

                    if not is_server_error or attempt == MAX_FETCH_RETRIES - 1:
                        # Final attempt failed or it's not a server error, raise the exception to abort
                        logger.error(
                            f"Pinecone fetch failed permanently after {attempt + 1} attempt(s)."
                        )
                        raise RuntimeError(
                            f"Failed to fetch existing IDs from Pinecone after {attempt + 1} retries."
                        ) from fetch_e
                    else:
                        # Wait before retrying server error
                        sleep_time = INITIAL_BACKOFF * (2**attempt)
                        logger.info(
                            f"Retrying fetch in {sleep_time} seconds due to server error..."
                        )
                        time.sleep(sleep_time)

        logger.info(f"Found {len(existing_ids)} existing chunk IDs in Pinecone.")
    except Exception as e:
        # Catch errors during the overall fetch process or the re-raised RuntimeError
        logger.error(f"Error during Pinecone ID fetch process: {e}", exc_info=True)
        # Re-raise as a runtime error to signal failure to the caller
        raise RuntimeError("Pinecone ingestion failed during ID fetch.") from e

    # Filter out chunks that already exist
    new_docs = [doc for doc in raw_docs if doc.metadata["post_id"] not in existing_ids]

    if not new_docs:
        logger.info("No new documents to ingest.")
    else:
        logger.info(f"Preparing to ingest {len(new_docs)} new documents.")

        # Ingest only the new chunks using LangchainPinecone helper
        try:
            # Create a list to track documents to remove due to summarization errors
            docs_to_remove = []

            for new_doc in new_docs:
                if new_doc.metadata["keywords"] == []:
                    try:
                        new_doc = gpt_summarize(new_doc)
                    except Exception as e:
                        # Mark document for removal instead of keeping it with empty keywords
                        logger.warning(
                            f"Error summarizing document {new_doc.metadata['post_id']}: {e}"
                        )
                        docs_to_remove.append(new_doc)

            # Remove documents that had errors during summarization
            if docs_to_remove:
                original_count = len(new_docs)
                new_docs = [doc for doc in new_docs if doc not in docs_to_remove]
                logger.info(
                    f"Excluded {original_count - len(new_docs)} documents due to summarization errors"
                )

            if not new_docs:
                logger.info("No documents to ingest after filtering out errors.")
                return

            vectorstore = LangchainPinecone(
                index=index, embedding=embedding, text_key="text"
            )  # Use text_key='text'
            vectorstore.add_documents(
                documents=new_docs,
                ids=[doc.metadata["post_id"] for doc in new_docs],
            )
            logger.info(
                f"Successfully added {len(new_docs)} new documents to Pinecone."
            )
        except Exception as e:
            logger.error(f"Error adding documents to Pinecone: {e}", exc_info=True)
            # Raise an exception to signal failure to the caller
            raise RuntimeError(
                "Pinecone ingestion failed during document addition."
            ) from e

    # Get final stats from Pinecone
    try:
        stats = index.describe_index_stats()
        logger.info(
            f"Pinecone index '{PINECONE_INDEX_NAME}' now has {stats.total_vector_count} total vectors."
        )
    except Exception as e:
        logger.warning(f"Could not retrieve final index stats from Pinecone: {e}")


if __name__ == "__main__":
    # Basic test execution - consider more robust testing
    try:
        ingest_docs()
        print("Ingestion script finished.")
    except Exception as main_e:
        print(f"Ingestion script failed: {main_e}")
        # In a real scenario, sys.exit(1) might be appropriate here
