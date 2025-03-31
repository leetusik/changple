import os
import uuid
from typing import List, Optional

from django.db.models import Q
from langchain_core.documents import Document
from whoosh.fields import DATETIME, ID, STORED, TEXT, Schema
from whoosh.index import create_in, open_dir

from scraper.models import AllowedAuthor, NaverCafeData


def create_whoosh_index(index_dir: str = "chatbot/data/whoosh_index"):
    """
    Create Whoosh index or append to existing index

    Args:
        index_dir: index directory path
    """
    # Convert to absolute path if it's a relative path
    abs_index_dir = os.path.abspath(index_dir)
    print(f"Creating/opening Whoosh index at absolute path: {abs_index_dir}")

    schema = Schema(
        post_id=ID(stored=True),  # original document's post_id (unique identifier)
        title=TEXT(stored=True),  # title field - searchable
        content=TEXT(stored=True),  # content
        author=TEXT(stored=True),  # author
        category=TEXT(stored=True),  # category
        published_date=STORED(),  # published date
        url=ID(stored=True),  # URL
    )

    # Ensure directory exists with proper permissions
    if not os.path.exists(abs_index_dir):
        print(f"Directory does not exist, creating: {abs_index_dir}")
        try:
            os.makedirs(abs_index_dir, exist_ok=True, mode=0o755)
            print(f"Successfully created directory: {abs_index_dir}")
        except Exception as e:
            print(f"Error creating directory {abs_index_dir}: {e}")
            raise

    # Check if index already exists (by checking for the TOC file)
    index_exists = os.path.exists(
        os.path.join(abs_index_dir, "MAIN_WRITELOCK")
    ) or os.path.exists(os.path.join(abs_index_dir, "TOC.txt"))

    if index_exists:
        try:
            print(f"Opening existing index at {abs_index_dir}")
            ix = open_dir(abs_index_dir)
            print("Successfully opened existing index")
        except Exception as e:
            print(f"Error opening existing index: {e}. Creating new index.")
            ix = create_in(abs_index_dir, schema)
            print(f"Created new index at {abs_index_dir}")
    else:
        print(f"Creating new index at {abs_index_dir}")
        ix = create_in(abs_index_dir, schema)
        print(f"Successfully created new index")

    print(f"Starting indexing process with writer...")
    writer = ix.writer()

    # get allowed authors list
    allowed_authors = list(
        AllowedAuthor.objects.filter(is_active=True).values_list("name", flat=True)
    )
    print(f"Allowed author count: {len(allowed_authors)}")

    # check total document count
    total_docs = NaverCafeData.objects.count()
    print(f"Total document count: {total_docs}")

    # get filtered documents
    posts = NaverCafeData.objects.filter(author__in=allowed_authors, vectorized=False)

    filtered_count = posts.count()
    print(f"Filtered document count: {filtered_count}")
    print(f"Document count to index: {posts.count()}")

    # convert to Document object and index
    indexed_count = 0
    for post in posts:
        writer.add_document(
            post_id=str(post.post_id),
            title=post.title or "",
            content=post.content,
            author=str(post.author) or "",
            category=post.category or "",
            published_date=post.published_date or "",
            url=post.url or "",
        )
        indexed_count += 1

        # show progress (every 1000 documents)
        if indexed_count % 1000 == 0:
            print(f"Progress: {indexed_count}/{posts.count()} documents indexed")

    writer.commit()
    print(f"Indexing completed: {indexed_count} documents added to index")

    # Verify index was created
    if os.path.exists(os.path.join(abs_index_dir, "TOC.txt")):
        print(f"Index verification successful - TOC.txt exists in {abs_index_dir}")
    else:
        print(
            f"WARNING: Index verification failed - TOC.txt does not exist in {abs_index_dir}"
        )

    return ix
