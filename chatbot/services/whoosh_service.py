import logging
import os
import uuid
from typing import List, Optional

from django.db.models import Q
from langchain_core.documents import Document
from whoosh.fields import DATETIME, ID, STORED, TEXT, Schema
from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser

from scraper.models import AllowedAuthor, AllowedCategory, NaverCafeData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_whoosh_index(index_dir: str = "chatbot/data/whoosh_index"):
    """
    Create Whoosh index incrementally or append new documents to an existing index.
    Only indexes documents from allowed authors/categories that are not already indexed.

    Args:
        index_dir: index directory path
    """
    # Define schema with post_id as unique identifier
    schema = Schema(
        post_id=ID(
            stored=True, unique=True
        ),  # original document's post_id (unique identifier)
        title=TEXT(stored=True),  # title field - searchable
        content=TEXT(stored=True),  # content
        author=TEXT(stored=True),  # author
        category=TEXT(stored=True),  # category
        published_date=STORED(),  # published date
        url=ID(stored=True),  # URL
    )

    if not os.path.exists(index_dir):
        os.makedirs(index_dir)

    # Check if index already exists
    index_exists = (
        os.path.exists(os.path.join(index_dir, "_MAIN_WRITELOCK"))
        or os.path.exists(os.path.join(index_dir, "MAIN_WRITELOCK"))
        or os.path.exists(os.path.join(index_dir, "_MAIN.toc"))
        or os.path.exists(os.path.join(index_dir, "MAIN.toc"))
    )

    ix = None
    indexed_post_ids = set()

    if index_exists:
        try:
            logger.info(f"Opening existing index at {index_dir}")
            ix = open_dir(index_dir)
            # Get IDs of already indexed documents
            with ix.searcher() as searcher:
                # Use reader().all_doc_ids() for efficiency if only IDs are needed?
                # No, need stored fields. Iterate through stored fields.
                logger.info("Reading existing document IDs from index...")
                for fields in searcher.all_stored_fields():
                    if "post_id" in fields:
                        indexed_post_ids.add(fields["post_id"])  # Add string ID
            logger.info(
                f"Found {len(indexed_post_ids)} existing documents in Whoosh index."
            )
        except Exception as e:
            logger.error(
                f"Error opening or reading existing index: {e}. Recreating index.",
                exc_info=True,
            )
            # If opening/reading fails, recreate the index
            try:
                ix = create_in(index_dir, schema)
                logger.info(f"Recreated new index at {index_dir} due to error.")
                index_exists = False  # Treat as new index
                indexed_post_ids = set()  # Reset existing IDs
            except Exception as create_e:
                logger.error(
                    f"Failed to recreate index after error: {create_e}. Aborting.",
                    exc_info=True,
                )
                return None  # Cannot proceed
    else:
        logger.info(f"Creating new index at {index_dir}")
        try:
            ix = create_in(index_dir, schema)
        except Exception as e:
            logger.error(f"Failed to create new index: {e}. Aborting.", exc_info=True)
            return None  # Cannot proceed

    # Get allowed authors/categories from DB
    try:
        allowed_authors = list(
            AllowedAuthor.objects.filter(is_active=True).values_list("name", flat=True)
        )
        logger.info(f"Allowed author count: {len(allowed_authors)}")
        allowed_categories = list(
            AllowedCategory.objects.filter(is_active=True).values_list(
                "name", flat=True
            )
        )
        logger.info(f"Allowed category count: {len(allowed_categories)}")
    except Exception as e:
        logger.error(
            f"Error fetching allowed authors/categories from DB: {e}. Aborting.",
            exc_info=True,
        )
        return ix  # Return index object, but cannot fetch posts

    # Get all relevant posts from DB
    try:
        posts_in_db = NaverCafeData.objects.filter(
            author__in=allowed_authors,
            category__in=allowed_categories,
            # Removed vectorized=False filter
        ).order_by(
            "id"
        )  # Order for consistency

        db_posts_map = {str(p.post_id): p for p in posts_in_db}  # Map ID to post object
        logger.info(
            f"Found {len(db_posts_map)} posts matching criteria in the database."
        )

    except Exception as e:
        logger.error(
            f"Error fetching posts from database: {e}. Aborting indexing run.",
            exc_info=True,
        )
        return ix  # Return index object, cannot add new docs

    # Determine which posts need to be added
    db_post_ids = set(db_posts_map.keys())
    ids_to_add = db_post_ids - indexed_post_ids
    posts_to_add = [db_posts_map[pid] for pid in ids_to_add]

    logger.info(f"Found {len(posts_to_add)} new documents to add to the Whoosh index.")

    # Add only the new documents
    if posts_to_add:
        try:
            writer = ix.writer(
                limitmb=256
            )  # Increase memory limit for writer if needed
            added_count = 0
            skipped_count = 0
            total_to_process = len(posts_to_add)

            for post in posts_to_add:
                try:
                    # Add document using post_id as string
                    writer.add_document(
                        post_id=str(post.post_id),
                        title=post.title or "",
                        content=post.content or "",  # Ensure content is not None
                        author=str(post.author) if post.author else "",
                        category=post.category or "",
                        published_date=post.published_date or "",
                        url=post.url or "",
                    )
                    added_count += 1

                    # show progress (every 1000 documents)
                    if added_count % 1000 == 0:
                        logger.info(
                            f"Indexing progress: {added_count}/{total_to_process} documents added"
                        )
                except Exception as doc_e:
                    logger.warning(
                        f"Error adding document for post_id {post.post_id}: {doc_e}. Skipping.",
                        exc_info=False,
                    )  # Log less verbose for per-doc errors
                    skipped_count += 1

            logger.info(f"Committing {added_count} new documents to the index...")
            writer.commit()
            logger.info(
                f"Indexing completed: {added_count} new documents added. {skipped_count} documents skipped due to errors."
            )
        except Exception as write_e:
            logger.error(
                f"Error during Whoosh writing/commit: {write_e}. Index might be partially updated.",
                exc_info=True,
            )
            # Optionally try to cancel the writer: writer.cancel()
    else:
        logger.info("No new documents found to add to the Whoosh index.")

    return ix
