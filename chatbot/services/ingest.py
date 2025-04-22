"""Load posts from database, clean up, split, ingest into Pinecone for RAG chatbot."""

import logging
import os
import time  # Added for retry sleep
from typing import List, Dict, Any

import django
from django.db.models import Q
from django.db.models.functions import Length
from dotenv import load_dotenv

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Now import Django models after setting up Django
from scraper.models import NaverCafeData

load_dotenv()

from langchain_community.vectorstores import Pinecone as LangchainPinecone
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec

from chatbot.services.content_evaluator import summary_and_keywords, QuestionItem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Custom exception for document processing control flow
class SkipDocumentError(Exception):
    """Exception raised when a document should be skipped from processing."""

    pass


def gpt_summarize(doc: Document) -> Document:
    """
    Process document: generate summary, keywords, and possible questions.
    Updates the document's metadata and the corresponding database entry.

    Args:
        doc: Document object with metadata including post_id, title, keywords, summary, and possible_questions

    Returns:
        Processed document with updated metadata

    Raises:
        SkipDocumentError: If the document should be skipped (e.g., DB lookup fails, generation fails)
    """
    post_id = doc.metadata["post_id"]
    db_object = None

    try:
        # Get the database object once at the beginning
        db_object = NaverCafeData.objects.get(post_id=post_id)
    except NaverCafeData.DoesNotExist:
        logger.error(f"Post with ID {post_id} not found in database")
        raise SkipDocumentError(f"Post with ID {post_id} not found in database")

    # Step 2: Process summary, keywords, and questions if needed
    # possible_questions가 있는지 확인 (이 함수는 load_posts_from_database에서 걸러진 것만 받으므로 항상 None일 것임)
    if doc.metadata["possible_questions"] is None:
        try:
            # Generate summary, keywords, and questions from the original content
            summary, keywords, possible_questions_list = summary_and_keywords(doc.page_content)

            # questions_list는 QuestionItem 객체의 리스트일 수 있으므로 문자열 리스트로 변환
            # content_evaluator.py의 반환 타입 변경에 맞춰 수정 필요 (이미 문자열 리스트로 반환한다면 이 변환은 불필요)
            # 만약 QuestionItem 객체 리스트로 반환된다면:
            if possible_questions_list and isinstance(possible_questions_list[0], QuestionItem):
                 questions_str_list = [item.question for item in possible_questions_list]
            else:
                 questions_str_list = possible_questions_list if isinstance(possible_questions_list, list) else []


            # Update metadata (DO NOT replace page_content)
            doc.metadata["summary"] = summary
            doc.metadata["keywords"] = keywords
            # questions_str_list를 metadata에 저장
            doc.metadata["possible_questions"] = questions_str_list
            logger.info(f"Generated summary, keywords, and questions for post_id {post_id}")

            # Update summary, keywords, and possible_questions in database
            db_object.summary = summary
            db_object.keywords = keywords
            # questions_str_list를 DB에 저장 (JSONField)
            db_object.possible_questions = questions_str_list
            db_object.save(update_fields=["summary", "keywords", "possible_questions"]) # possible_questions 추가
        except ValueError as e: # Catch specific error from summary_and_keywords
             logger.error(
                f"Failed to generate summary/keywords/questions for post_id {post_id}: {e}"
            )
             raise SkipDocumentError(f"Failed to generate summary/keywords/questions: {e}")
        except Exception as e: # Catch other potential errors
            logger.error(
                f"Unexpected error during generation/DB update for post_id {post_id}: {e}"
            )
            raise SkipDocumentError(f"Unexpected error processing post: {e}")
    else:
        # 이미 possible_questions가 있는 경우 (이론상 load_posts_from_database 필터링 때문에 여기 오지 않음)
        logger.info(f"Post {post_id} already has possible_questions. Skipping generation.")


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
    Only retrieve posts from allowed authors and categories where possible_questions is null.

    Returns:
        List of Documents
    """
    try:
        # Use proper Length annotation instead of unsupported len lookup
        # Updated filter to check for null possible_questions
        posts = (
            NaverCafeData.objects.annotate(content_length=Length("content"))
            .filter(
                author__in=[
                    "창플",
                ],
                content_length__gt=min_content_length,
                possible_questions__isnull=True
            )
        )

        logger.info(
            f"Loaded {posts.count()} posts matching criteria (author, length > {min_content_length}, missing possible_questions) from database"
        )

        documents = []
        for post in posts:
            temp_search_field = post.content
            # Handle None value for notation
            notation_value = post.notation if post.notation is not None else "none"

            # Create document with metadata
            doc = Document(
                page_content=temp_search_field,
                metadata={
                    "post_id": post.post_id,
                    "title": post.title,
                    "keywords": post.keywords,
                    "summary": post.summary,
                    "possible_questions": post.possible_questions,
                    "notation": notation_value, 
                    "full_content": post.content,
                },
            )
            documents.append(doc)

        return documents
    except Exception as e:
        logger.error(f"Error loading posts from database: {e}")
        return []


def ingest_docs():
    """
    Load posts missing possible_questions from database, generate summary/keywords/questions,
    update DB, and ingest/update documents in Pinecone using post_id as the vector ID.
    Uses retries for Pinecone fetch operations.
    Raises RuntimeError if ingestion fails critically (e.g., fetch after retries).
    """
    PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
    PINECONE_ENVIRONMENT = os.environ["PINECONE_ENVIRONMENT"]
    PINECONE_INDEX_NAME = os.environ["PINECONE_INDEX_NAME"]
    # MAX_FETCH_RETRIES = 3
    # INITIAL_BACKOFF = 2  # seconds

    # Get embedding model
    embedding = get_embeddings_model()

    # Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)

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

    # Process documents to generate summary/keywords and update DB
    processed_docs = []
    total_docs = len(raw_docs)
    for idx, raw_doc in enumerate(raw_docs, 1):
        try:
            # Process the document (generate summary/keywords)
            processed_doc = gpt_summarize(raw_doc) # Updates DB and doc.metadata
            processed_docs.append(processed_doc)
            logger.info(f"{idx}/{total_docs} documents processed")
        except SkipDocumentError as skip_e:
            logger.info(
                f"Skipping document with post_id {raw_doc.metadata['post_id']} during processing: {skip_e}"
            )
        except Exception as e:
            logger.error(
                f"Error processing document with post_id {raw_doc.metadata['post_id']}: {e}"
            )

    if not processed_docs:
        logger.info("No documents successfully processed. Nothing to ingest.")
        return

    # Now handle ingestion/update to Pinecone
    # We will upsert the processed documents, replacing existing ones if necessary.
    logger.info(f"Preparing to upsert {len(processed_docs)} documents to Pinecone.")

    try:
        vectorstore = LangchainPinecone(
            index=index, embedding=embedding, text_key="search_field"
        )

        # Batch documents for embedding and upsertion
        embedding_batch_size = 20 # Consider Pinecone limits if issues arise
        total_batches = (len(processed_docs) - 1) // embedding_batch_size + 1

        for i in range(0, len(processed_docs), embedding_batch_size):
            batch_docs = processed_docs[i : i + embedding_batch_size]
            batch_ids = [str(doc.metadata["post_id"]) for doc in batch_docs]

            # --- 임베딩할 텍스트 생성 로직 추가 ---
            docs_to_embed = []
            for doc in batch_docs:
                title = doc.metadata.get("title", "")
                summary = doc.metadata.get("summary", "")
                keywords_list = doc.metadata.get("keywords", [])
                questions_list = doc.metadata.get("possible_questions", []) # gpt_summarize에서 문자열 리스트로 저장됨

                # 키워드와 질문 포맷팅
                keywords_str = " ".join(keywords_list)
                questions_str = "\n".join(questions_list) # 각 질문을 줄바꿈으로 구분

                # 임베딩을 위한 텍스트 생성 (요약 + 키워드 + 질문 형식)
                text_for_embedding = f"""
제목: {title}
요약: {summary}
키워드: {keywords_str}
질문: 
{questions_str}"""

                # 원본 Document 객체를 복사하여 page_content만 교체 (metadata 유지)
                doc.page_content = text_for_embedding
                docs_to_embed.append(doc)
            # --- 임베딩할 텍스트 생성 로직 끝 ---


            logger.info(
                f"Upserting batch {i//embedding_batch_size + 1}/{total_batches} with {len(docs_to_embed)} documents to Pinecone..."
            )

            # Use add_documents which internally handles upsert based on IDs
            # The document's page_content (NOW the combined text) is embedded.
            # The metadata (including the original summary, keywords, etc.) is stored.
            vectorstore.add_documents(
                documents=docs_to_embed,
                ids=batch_ids,
            )

            logger.info(
                f"Successfully upserted batch {i//embedding_batch_size + 1} to Pinecone."
            )

        logger.info(
            f"Successfully upserted {len(processed_docs)} processed documents to Pinecone."
        )

    except Exception as e:
        logger.error(f"Error upserting documents to Pinecone: {e}", exc_info=True)
        raise RuntimeError(
            "Pinecone ingestion failed during document upsert."
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
