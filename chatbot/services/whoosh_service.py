import os
import uuid
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, DATETIME, STORED
from langchain_core.documents import Document
from typing import List, Optional
from django.db.models import Q
from scraper.models import AllowedAuthor, NaverCafeData

def create_whoosh_index(index_dir: str = "chatbot/data/whoosh_index"):
    """
    Create Whoosh index
    
    Args:
        index_dir: index directory path
    """
    schema = Schema(
        post_id=ID(stored=True),           # original document's post_id (unique identifier)
        title=TEXT(stored=True),           # title field - searchable
        content=TEXT(stored=True),         # content
        author=TEXT(stored=True),          # author
        category=TEXT(stored=True),        # category
        published_date=STORED(),           # published date
        url=ID(stored=True)                # URL
    )
    
    if not os.path.exists(index_dir):
        os.makedirs(index_dir)
    
    ix = create_in(index_dir, schema)
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
    posts = NaverCafeData.objects.filter(
        author__in=allowed_authors,
        vectorized=True
    )

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
            url=post.url or ""
        )
        indexed_count += 1

        # show progress (every 1000 documents)
        if indexed_count % 1000 == 0:
            print(f"Progress: {indexed_count}/{posts.count()} documents indexed")

    writer.commit()
    print(f"Indexing completed: {indexed_count} documents")
    return ix

