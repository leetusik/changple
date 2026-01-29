"""
OpenAI Batch API for embeddings (50% cost savings).

https://platform.openai.com/docs/api-reference/batch
"""

import json
import logging
import os
import tempfile
from typing import List, Optional

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def submit_embedding_batch(texts: List[str], custom_ids: List[str]) -> Optional[str]:
    """
    Submit embedding batch to OpenAI Batch API.

    Args:
        texts: List of texts to embed
        custom_ids: List of custom IDs (post_ids) for tracking

    Returns:
        batch_id for polling, or None if failed

    Note: OpenAI Batch API provides 50% cost savings with 24-hour SLA.
    """
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Create JSONL file
        requests = []
        for custom_id, text in zip(custom_ids, texts):
            requests.append(
                {
                    "custom_id": str(custom_id),
                    "method": "POST",
                    "url": "/v1/embeddings",
                    "body": {
                        "model": "text-embedding-3-large",
                        "input": text,
                    },
                }
            )

        # Write to temp file and upload
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            for req in requests:
                f.write(json.dumps(req) + "\n")
            temp_path = f.name

        try:
            # Upload file
            with open(temp_path, "rb") as f:
                uploaded = client.files.create(file=f, purpose="batch")

            # Create batch
            batch = client.batches.create(
                input_file_id=uploaded.id,
                endpoint="/v1/embeddings",
                completion_window="24h",
            )

            logger.info(f"Submitted OpenAI embedding batch: {batch.id}")
            return batch.id

        finally:
            # Clean up temp file
            os.unlink(temp_path)

    except ImportError:
        logger.error("openai package not installed")
        return None
    except Exception as e:
        logger.error(f"Failed to submit OpenAI embedding batch: {e}")
        return None


def check_embedding_batch(batch_id: str) -> tuple[str, Optional[dict]]:
    """
    Check status of an OpenAI embedding batch.

    Args:
        batch_id: The batch ID returned from submit_embedding_batch

    Returns:
        Tuple of (status, results):
        - status: "processing", "completed", "failed"
        - results: Dict mapping custom_id -> embedding vector if completed
    """
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        batch = client.batches.retrieve(batch_id)

        if batch.status == "completed":
            # Download results
            results = {}

            if batch.output_file_id:
                output_content = client.files.content(batch.output_file_id)
                for line in output_content.text.strip().split("\n"):
                    try:
                        data = json.loads(line)
                        custom_id = data["custom_id"]
                        embedding = data["response"]["body"]["data"][0]["embedding"]
                        results[custom_id] = embedding
                    except Exception as e:
                        logger.error(f"Failed to parse batch response line: {e}")

            return "completed", results

        elif batch.status in ("failed", "cancelled", "expired"):
            logger.error(f"Batch job failed: {batch.status}")
            return "failed", None

        else:
            # Still processing (validating, in_progress, finalizing)
            return "processing", None

    except ImportError:
        logger.error("openai package not installed")
        return "failed", None
    except Exception as e:
        logger.error(f"Failed to check OpenAI embedding batch: {e}")
        return "failed", None


def ingest_embeddings_to_pinecone(batch_job, embeddings: dict) -> int:
    """
    Ingest embeddings to Pinecone and update database.

    Args:
        batch_job: BatchJob model instance
        embeddings: Dict mapping post_id -> embedding vector

    Returns:
        Number of successfully ingested posts
    """
    from pinecone import Pinecone

    from src.scraper.models import NaverCafeData

    pc = Pinecone(api_key=settings.PINECONE_API_KEY, transport="http")
    index = pc.Index(settings.PINECONE_INDEX_NAME)

    # Prepare vectors for upsert
    vectors_to_upsert = []
    post_ids_to_mark = []

    for post_id_str, embedding in embeddings.items():
        post_id = int(post_id_str)
        try:
            post = NaverCafeData.objects.get(post_id=post_id)

            # Prepare metadata
            metadata = {
                "title": post.title,
                "author": post.author,
                "summary": post.summary or "",
                "keywords": ",".join(post.keywords or []),
                "questions": ",".join(post.possible_questions or []),
            }

            vectors_to_upsert.append(
                {
                    "id": str(post_id),
                    "values": embedding,
                    "metadata": metadata,
                }
            )
            post_ids_to_mark.append(post_id)

        except NaverCafeData.DoesNotExist:
            logger.error(f"Post {post_id} not found in database")
        except Exception as e:
            logger.error(f"Failed to prepare post {post_id} for Pinecone: {e}")

    # Upsert to Pinecone in batches
    batch_size = 100
    ingested_count = 0

    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i : i + batch_size]
        try:
            index.upsert(vectors=batch)
            ingested_count += len(batch)
            logger.info(f"Upserted {len(batch)} vectors to Pinecone")
        except Exception as e:
            logger.error(f"Failed to upsert batch to Pinecone: {e}")

    # Mark posts as ingested
    if post_ids_to_mark:
        from django.db import transaction

        with transaction.atomic():
            NaverCafeData.objects.filter(post_id__in=post_ids_to_mark).update(
                ingested=True
            )
            logger.info(f"Marked {len(post_ids_to_mark)} posts as ingested")

    # Update batch job status
    batch_job.status = "completed"
    batch_job.completed_at = timezone.now()
    batch_job.save()

    return ingested_count
