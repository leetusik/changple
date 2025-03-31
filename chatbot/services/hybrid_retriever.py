from typing import List, Any
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from whoosh import scoring
from whoosh.index import open_dir
from whoosh.qparser import MultifieldParser
from pydantic import Field
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

class HybridRetriever(BaseRetriever):
    """Hybrid Retriever using Vector Search and BM25"""
    
    vectorstore: Any = Field(None, description="Vector store instance")
    whoosh_ix: Any = Field(None, description="Whoosh index instance")
    alpha: float = Field(0.5, description="Weight between vector and BM25 scores")
    k: int = Field(3, description="Number of documents to return")
    vector_results: List = Field(default_factory=list, description="Vector search results")
    bm25_results: List = Field(default_factory=list, description="BM25 search results")
    
    # 새로 추가할 필드들
    keyword_llm: Any = Field(None, description="LLM for keyword extraction")
    keyword_prompt: Any = Field(None, description="Prompt template for keyword extraction")
    keyword_chain: Any = Field(None, description="Chain for keyword extraction")
    
    def __init__(
        self,
        vector_store,
        whoosh_index_dir: str = "chatbot/data/whoosh_index",
        alpha: float = 0.5,
        k: int = 3,
        keyword_model: str = "gpt-4o-mini"  # llm for keyword extraction
    ):
        """
        Args:
            vector_store: vector store instance
            whoosh_index_dir: path to Whoosh index directory
            alpha: weight between vector and BM25 scores (0~1)
            k: number of documents to return
            keyword_model: llm for keyword extraction
        """
        super().__init__()
        self.vectorstore = vector_store
        
        # add instance variables to store results
        self.vector_results = []
        self.bm25_results = []
        
        # check and open Whoosh index
        if not os.path.exists(whoosh_index_dir):
            raise FileNotFoundError(
                "Whoosh index not found. "
                "Please run the following command to create the index:\n"
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
        
        # 키워드 추출용 LLM 모델 초기화
        self.keyword_llm = ChatOpenAI(model=keyword_model, temperature=0)
        self.keyword_prompt = PromptTemplate.from_template(
            "당신은 BM25 검색에 적합한 키워드 추출 전문가입니다."
            "다음 문장에서 질문의 의도를 가장 잘 나타내는 중요한 BM25 검색 키워드를 2개 이내로 추출하세요. "
            "키워드만 공백으로 구분하여 출력하세요. 접속사, 조사 등은 제거하세요.\n\n"
            "문장: {query}\n\n"
            "키워드:"
        )
        self.keyword_chain = self.keyword_prompt | self.keyword_llm | StrOutputParser()
    
    def extract_keywords(self, query: str) -> str:
        """
        Convert a sentence-based query into a BM25-search-friendly keyword format.
        
        Args:
            query: user input query sentence
            
        Returns:
            str: extracted keywords (separated by spaces)
        """
        try:
            # use LLM to extract keywords
            keywords = self.keyword_chain.invoke({"query": query})
            
            # return original query if result is empty or error occurs
            if not keywords or len(keywords.strip()) == 0:
                return query
                
            return keywords.strip()
        except Exception as e:# return original query if error occurs
            print(f"Error occurred during keyword extraction: {str(e)}")
            return query

    def _get_relevant_documents(
        self, query: str, *, run_manager=None
    ) -> List[Document]:
        
        MULTIPLIER = 5

        # vector search
        self.vector_results = self.vectorstore.vectorstore.similarity_search_with_relevance_scores(
            query, k=self.k * MULTIPLIER
        )
        
        # BM25 search - use keyword-converted query
        bm25_query = self.extract_keywords(query)
        print(f"Original query: '{query}'\n → BM25 keywords: '{bm25_query}'")
        
        with self.whoosh_ix.searcher(weighting=scoring.BM25F(
            title_B=2.0,
            content_B=1.0
        )) as searcher:
            parser = MultifieldParser(["title", "content"], self.whoosh_ix.schema)
            whoosh_query = parser.parse(f'({bm25_query})')
            print(f"Whoosh AND 쿼리: {whoosh_query}")
            whoosh_results = searcher.search(whoosh_query, limit=self.k * MULTIPLIER)
            
            # if results are less than half of k, use OR search
            if len(whoosh_results) < self.k * 0.5:
                print(f"AND 검색 결과 부족 ({len(whoosh_results)}개). OR 검색으로 전환")
                whoosh_query = parser.parse(' OR '.join(bm25_query.split()))
                print(f"Whoosh OR 쿼리: {whoosh_query}")
                whoosh_results = searcher.search(whoosh_query, limit=self.k * MULTIPLIER)
            
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
                        "url": r.get("url", ""),
                        "vector_score": 0,
                        "bm25_score": r.score
                    }
                ), r.score) 
                for r in whoosh_results
            ]

        # normalize scores and combine
        combined_scores = {}
        
        # vector search results
        if self.vector_results:  # if results exist, normalize
            max_vector_score = max(score for _, score in self.vector_results)
            for doc, score in self.vector_results:
                # add initial values to metadata
                if "vector_score" not in doc.metadata:
                    doc.metadata["vector_score"] = 0
                if "bm25_score" not in doc.metadata:
                    doc.metadata["bm25_score"] = 0
                
                # save original vector search score
                doc.metadata["vector_score"] = score
                
                # post_id to string
                doc_id = str(int(doc.metadata.get("post_id"))) if doc.metadata.get("post_id") is not None else None
                normalized_score = score / max_vector_score if max_vector_score > 0 else 0
                combined_scores[doc_id] = {
                    "doc": doc,
                    "score": self.alpha * normalized_score
                }

        
        # BM25 results
        print(f"BM25 search document count: {len(self.bm25_results)}")
        if self.bm25_results:  # if results exist, normalize
            max_bm25_score = max(score for _, score in self.bm25_results)
            for doc, score in self.bm25_results:
                doc_id = doc.metadata.get("post_id")
                normalized_score = score / max_bm25_score if max_bm25_score > 0 else 0
                if doc_id in combined_scores:
                    combined_scores[doc_id]["score"] += (1 - self.alpha) * normalized_score
                    # add BM25 score to existing document
                    combined_scores[doc_id]["doc"].metadata["bm25_score"] = score
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
        
        # save final score to metadata
        for item in sorted_results[:self.k]:
            item["doc"].metadata["combined_score"] = item["score"]

        return [item["doc"] for item in sorted_results[:self.k]]  # pick top k

    async def _aget_relevant_documents(
        self, query: str, *, run_manager=None
    ) -> List[Document]:
        # async implementation if needed
        return self._get_relevant_documents(query)
