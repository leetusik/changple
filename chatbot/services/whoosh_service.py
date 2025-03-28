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
    Whoosh 인덱스 생성
    
    Args:
        index_dir: 인덱스 디렉토리 경로
    """
    schema = Schema(
        post_id=ID(stored=True),           # 원래 문서의 post_id (고유 식별자)
        title=TEXT(stored=True),           # 제목 필드 - 검색 가능
        content=TEXT(stored=True),         # 본문 내용
        author=TEXT(stored=True),          # 작성자
        category=TEXT(stored=True),        # 카테고리
        published_date=STORED(),           # 발행일
        url=ID(stored=True)                # URL
    )
    
    if not os.path.exists(index_dir):
        os.makedirs(index_dir)
    
    ix = create_in(index_dir, schema)
    writer = ix.writer()
    
    # 허용된 작성자 목록 가져오기
    allowed_authors = list(
        AllowedAuthor.objects.filter(is_active=True).values_list("name", flat=True)
    )
    print(f"허용된 작성자 수: {len(allowed_authors)}")

    # 전체 문서 수 확인
    total_docs = NaverCafeData.objects.count()
    print(f"전체 문서 수: {total_docs}")

    # 필터링된 문서 가져오기
    posts = NaverCafeData.objects.filter(
        author__in=allowed_authors,
        vectorized=True
    )

    filtered_count = posts.count()
    print(f"필터링된 문서 수: {filtered_count}")
    print(f"인덱싱할 문서 수: {posts.count()}")
    
    # Document 객체로 변환하고 인덱싱
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

        # 진행상황 표시 (1000개마다)
        if indexed_count % 1000 == 0:
            print(f"진행 중: {indexed_count}/{posts.count()} 문서 인덱싱 완료")

    writer.commit()
    print(f"인덱싱 완료: {indexed_count}개 문서")
    return ix

