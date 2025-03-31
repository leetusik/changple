from typing import List, Any
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from whoosh import scoring
from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser, MultifieldParser
from pydantic import Field
from whoosh.fields import Schema, TEXT, ID, STORED
import os

class HybridRetriever(BaseRetriever):
    """Vector Store와 BM25를 결합한 하이브리드 검색 리트리버"""
    
    vectorstore: Any = Field(None, description="Vector store instance")
    whoosh_ix: Any = Field(None, description="Whoosh index instance")
    alpha: float = Field(0.5, description="Weight between vector and BM25 scores")
    k: int = Field(4, description="Number of documents to return")
    
    def __init__(
        self,
        vector_store,
        whoosh_index_dir: str = "chatbot/data/whoosh_index",
        alpha: float = 0.5,
        k: int = 4
    ):
        """
        Args:
            vector_store: 벡터 스토어 인스턴스
            whoosh_index_dir: Whoosh 인덱스 디렉토리 경로
            alpha: 벡터 검색과 BM25 점수의 가중치 (0~1)
            k: 반환할 문서 수
        """
        super().__init__()
        self.vectorstore = vector_store
        
        # 결과를 저장할 인스턴스 변수 추가
        self.vector_results = []
        self.bm25_results = []
        
        # Whoosh 인덱스 확인 및 열기
        if not os.path.exists(whoosh_index_dir):
            raise FileNotFoundError(
                "Whoosh 인덱스를 찾을 수 없습니다. "
                "다음 명령어를 실행하여 인덱스를 생성해주세요:\n"
                "python manage.py run_whoosh_index"
            )
        
        try:
            self.whoosh_ix = open_dir(whoosh_index_dir)
        except Exception as e:
            raise Exception(
                f"Whoosh 인덱스를 여는 중 오류가 발생했습니다: {str(e)}\n"
                "인덱스가 손상되었을 수 있습니다. 다음 명령어로 재생성해주세요:\n"
                "python manage.py run_whoosh_index"
            )
        
        self.alpha = alpha
        self.k = k

    def _get_relevant_documents(
        self, query: str, *, run_manager=None
    ) -> List[Document]:
        # vector search
        self.vector_results = self.vectorstore.vectorstore.similarity_search_with_relevance_scores(
            query, k=self.k * 3
        )
        
        # BM25 search
        with self.whoosh_ix.searcher(weighting=scoring.BM25F(
            title_B=2.0,
            content_B=1.0
        )) as searcher:
            whoosh_query = MultifieldParser(["title", "content"], 
                                          self.whoosh_ix.schema).parse(query)
            print("BM25 검색 query: ", whoosh_query)
            whoosh_results = searcher.search(whoosh_query, limit=self.k * 3) 
            print("BM25 검색 결과: ", whoosh_results)

            # Whoosh results (Document, score) 
            self.bm25_results = [
                (Document(
                    page_content=r["content"], 
                    metadata={
                        "post_id": r["post_id"],
                        "title": r["title"],
                        "author": r.get("author", ""),
                        "category": r.get("category", ""),
                        "published_date": r.get("published_date", ""),
                        "url": r.get("url", "")
                    }
                ), r.score) 
                for r in whoosh_results
            ]

        # normalize scores and combine
        combined_scores = {}
        
        # vector search results
        if self.vector_results:  # 결과가 있는 경우에만 정규화
            max_vector_score = max(score for _, score in self.vector_results)
            for doc, score in self.vector_results:
                doc_id = doc.metadata.get("post_id")
                normalized_score = score / max_vector_score if max_vector_score > 0 else 0
                combined_scores[doc_id] = {
                    "doc": doc,
                    "score": self.alpha * normalized_score
                }

        # BM25 results
        if self.bm25_results:  # 결과가 있는 경우에만 정규화
            max_bm25_score = max(score for _, score in self.bm25_results)
            for doc, score in self.bm25_results:
                doc_id = doc.metadata.get("post_id")
                normalized_score = score / max_bm25_score if max_bm25_score > 0 else 0
                if doc_id in combined_scores:
                    combined_scores[doc_id]["score"] += (1 - self.alpha) * normalized_score
                else:
                    combined_scores[doc_id] = {
                        "doc": doc,
                        "score": (1 - self.alpha) * normalized_score
                    }

        # final results
        sorted_results = sorted(
            combined_scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )
        
        return [item["doc"] for item in sorted_results[:self.k]]  # pick top k

    async def _aget_relevant_documents(
        self, query: str, *, run_manager=None
    ) -> List[Document]:
        # async implementation if needed
        return self._get_relevant_documents(query)
