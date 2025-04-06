import logging
import math
import os
import statistics
from typing import Any, List

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_openai import ChatOpenAI
from pydantic import Field
from whoosh import scoring
from whoosh.index import EmptyIndexError, open_dir
from whoosh.qparser import MultifieldParser
from django.conf import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridRetriever(BaseRetriever):
    """Hybrid Retriever using Vector Search and BM25"""

    vectorstore: Any = Field(None, description="Vector store instance")
    whoosh_ix: Any = Field(None, description="Whoosh index instance")
    alpha: float = Field(0.5, description="Weight between vector and BM25 scores")
    k: int = Field(3, description="Number of documents to return")
    vector_results: List = Field(
        default_factory=list, description="Vector search results"
    )
    bm25_results: List = Field(default_factory=list, description="BM25 search results")

    # 새로 추가할 필드들
    keyword_llm: Any = Field(None, description="LLM for keyword extraction")
    keyword_prompt: Any = Field(
        None, description="Prompt template for keyword extraction"
    )
    keyword_chain: Any = Field(None, description="Chain for keyword extraction")

    def __init__(
        self,
        vector_store,
        whoosh_index_dir: str = settings.WHOOSH_INDEX_DIR,
        alpha: float = settings.HYBRID_ALPHA,
        k: int = settings.NUM_DOCS,
        keyword_model: str = settings.KEYWORD_MODEL,  # llm for keyword extraction
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

        # Try to open Whoosh index, disable BM25 if it fails
        try:
            if not os.path.exists(whoosh_index_dir):
                logger.warning(
                    f"Whoosh index directory not found at {whoosh_index_dir}. BM25 search will be disabled."
                )
                self.whoosh_ix = None
            else:
                self.whoosh_ix = open_dir(whoosh_index_dir)
                logger.info(
                    f"Whoosh index loaded successfully from {whoosh_index_dir}."
                )
        except EmptyIndexError:
            logger.warning(
                f"Whoosh index at {whoosh_index_dir} is empty. BM25 search will be disabled."
            )
            self.whoosh_ix = None
        except Exception as e:
            logger.warning(
                f"Failed to open Whoosh index at {whoosh_index_dir}: {e}. BM25 search will be disabled."
            )
            self.whoosh_ix = None

        self.alpha = alpha
        self.k = k

        # 키워드 추출용 LLM 모델 초기화
        self.keyword_llm = ChatOpenAI(model=keyword_model, temperature=0)
        self.keyword_prompt = PromptTemplate.from_template(
            "당신은 관련된 문서를 검색하기 위한 키워드 추출 전문가입니다."
            "아래에 주어진 대화 이력을 바탕으로 사용자가 문의하고자 하는 내용에 대해 관련 문서를 가장 잘 찾을 수 있는 long-tail 검색 키워드를 추출하세요."
            "키워드는 가장 적절한 것으로 최대 4단어까지 추출할 수 있습니다. 단어 사이는 공백으로 구분하세요."
            "창업, 사업, 방법, 조언 같은 너무 흔한 키워드는 제외하세요."
            "접속사, 조사, 문장 부호 등은 반드시 제거하고 키워드만 출력해야 합니다.\n\n"
            "대화 이력: {chat_history}\n\n"
            "키워드:"
        )
        self.keyword_chain = self.keyword_prompt | self.keyword_llm | StrOutputParser()

    def extract_keywords(self, chat_history: str) -> str:
        """
        Convert a sentence-based query into a BM25-search-friendly keyword format.

        Args:
            chat_history: chat history with user

        Returns:
            str: extracted keywords (separated by spaces)
        """
        # chat_history : f"대화 기록: ~~~ \n\n현재 질문: {x['question']}"
        last_question = chat_history.split("현재 질문: ")[-1].strip()

        try:
            # use LLM to extract keywords
            keywords = self.keyword_chain.invoke({"chat_history": chat_history})

            # return original query if result is empty or error occurs
            if not keywords or len(keywords.strip()) == 0:
                return last_question

            return keywords.strip()
        except Exception as e: 
            logger.error(f"Error occurred during keyword extraction: {str(e)}")
            return last_question

    def _get_relevant_documents(
        self, chat_history: str, *, run_manager=None
    ) -> List[Document]:

        # Reset results for this query
        self.vector_results = []
        self.bm25_results = []

        MULTIPLIER = 5

        search_query = self.extract_keywords(chat_history)

        # vector search
        try:
            self.vector_results = (
                self.vectorstore.vectorstore.similarity_search_with_relevance_scores(
                    search_query, k=self.k * MULTIPLIER
                )
            )
        except Exception as e:
            logger.error(f"Error during vector search: {e}")
            self.vector_results = []  # Ensure it's empty on error


        # BM25 search - use keyword-converted query only if index is available
        if self.whoosh_ix:
            try: 
                logger.info(
                    f"BM25 keywords: '{search_query}'"
                )

                with self.whoosh_ix.searcher(
                    weighting=scoring.BM25F(title_B=2.0, content_B=1.0)
                ) as searcher:
                    parser = MultifieldParser(
                        ["title", "content"], self.whoosh_ix.schema
                    )

                    # Try AND search first
                    whoosh_query_and = parser.parse(f"({search_query})")
                    whoosh_results = searcher.search(
                        whoosh_query_and, limit=self.k * MULTIPLIER
                    )

                    # if results are less than half of k *and* there are multiple keywords, use OR search
                    if len(whoosh_results) < self.k * 0.5 and " " in search_query.strip():
                        whoosh_query_or = parser.parse(" OR ".join(search_query.split()))
                        whoosh_results = searcher.search(
                            whoosh_query_or, limit=self.k * MULTIPLIER
                        )

                    # Whoosh results (Document, score)
                    self.bm25_results = [
                        (
                            Document(
                                page_content=r["content"],
                                metadata={
                                    "post_id": str(
                                        r["post_id"]
                                    ),  # Ensure post_id is string
                                    "title": r["title"],
                                    "author": r.get("author", ""),
                                    "category": r.get("category", ""),
                                    "published_date": r.get("published_date", ""),
                                    "url": r.get("url", ""),
                                    "vector_score": 0,  # Initialize scores
                                    "bm25_score": r.score,
                                },
                            ),
                            r.score,
                        )
                        for r in whoosh_results
                    ]
            except Exception as e:
                logger.error(f"Error during BM25 search: {e}")
                self.bm25_results = []  # Ensure empty on error
        else:
            logger.warning("BM25 search skipped: Whoosh index not available.")
            self.bm25_results = []  # Ensure it's empty

        # normalize scores and combine
        combined_scores = {}

        # vector search results
        if self.vector_results:
            vector_scores = [score for _, score in self.vector_results]

            # Z-score standardization
            if len(vector_scores) > 1:
                vector_mean = statistics.mean(vector_scores)
                vector_stdev = statistics.stdev(vector_scores)

                for doc, score in self.vector_results:
                    # Ensure scores initialized in metadata
                    doc.metadata.setdefault("vector_score", 0)
                    doc.metadata.setdefault("bm25_score", 0)
                    doc.metadata["vector_score"] = score

                    # Handle potential missing or non-int post_id from vector store
                    post_id_val = doc.metadata.get("post_id")
                    doc_id = None
                    if post_id_val is not None:
                        try:
                            doc_id = str(int(post_id_val))
                        except (ValueError, TypeError):
                            pass

                    if doc_id:  # Only process if doc_id exists and is valid string
                        # Z-score standardization
                        normalized_score = (
                            (score - vector_mean) / vector_stdev
                            if vector_stdev > 0
                            else 0
                        )

                        # normalized scores may be too large, so convert to sigmoid function and normalize to 0~1
                        normalized_score = 1 / (1 + math.exp(-normalized_score))

                        combined_scores[doc_id] = {
                            "doc": doc,
                            "score": self.alpha * normalized_score,
                        }
                    else:
                        pass

            elif (
                len(vector_scores) == 1
            ):  # if there is only one value, set normalized score to 1
                doc, score = self.vector_results[0]
                doc.metadata.setdefault("vector_score", 0)
                doc.metadata.setdefault("bm25_score", 0)
                doc.metadata["vector_score"] = score

                post_id_val = doc.metadata.get("post_id")
                doc_id = None
                if post_id_val is not None:
                    try:
                        doc_id = str(int(post_id_val))
                    except (ValueError, TypeError):
                        pass

                if doc_id:  # Only process if doc_id exists and is valid string
                    combined_scores[doc_id] = {
                        "doc": doc,
                        "score": self.alpha * 1,  # single score is normalized to 1
                    }
                else:
                    pass

        # BM25 results
        if self.bm25_results:
            bm25_scores = [score for _, score in self.bm25_results]

            # Z-score standardization
            if len(bm25_scores) > 1:
                bm25_mean = statistics.mean(bm25_scores)
                bm25_stdev = statistics.stdev(bm25_scores)

                for doc, score in self.bm25_results:
                    doc_id = doc.metadata.get(
                        "post_id"
                    )  # Should be string from Whoosh processing above

                    if (
                        doc_id
                    ):  # Only process if doc_id exists (should always exist here)
                        # Z-score standardization
                        normalized_score = (
                            (score - bm25_mean) / bm25_stdev if bm25_stdev > 0 else 0
                        )

                        # normalized scores may be too large, so convert to sigmoid function and normalize to 0~1
                        normalized_score = 1 / (1 + math.exp(-normalized_score))

                        if doc_id in combined_scores:
                            combined_scores[doc_id]["score"] += (
                                1 - self.alpha
                            ) * normalized_score
                            # add BM25 score to existing document
                            combined_scores[doc_id]["doc"].metadata[
                                "bm25_score"
                            ] = score
                        else:
                            # Ensure scores initialized if adding new doc from BM25
                            doc.metadata.setdefault(
                                "vector_score", 0
                            )  # Should already be 0 from doc creation
                            doc.metadata["bm25_score"] = (
                                score  # Already set during doc creation
                            )
                            combined_scores[doc_id] = {
                                "doc": doc,
                                "score": (1 - self.alpha) * normalized_score,
                            }
                    else:
                        pass

            elif (
                len(bm25_scores) == 1
            ):  # if there is only one value, set normalized score to 1
                doc, score = self.bm25_results[0]
                doc_id = doc.metadata.get("post_id")
                if doc_id:  # Only process if doc_id exists
                    if doc_id in combined_scores:
                        combined_scores[doc_id]["score"] += (1 - self.alpha) * 1
                        combined_scores[doc_id]["doc"].metadata["bm25_score"] = score
                    else:
                        doc.metadata.setdefault("vector_score", 0)
                        doc.metadata["bm25_score"] = (
                            score  # Already set during doc creation
                        )
                        combined_scores[doc_id] = {
                            "doc": doc,
                            "score": (1 - self.alpha)
                            * 1,  # single score is normalized to 1
                        }
                else:
                    pass

        # final results
        sorted_results = sorted(
            combined_scores.values(), key=lambda x: x["score"], reverse=True
        )

        # save final score to metadata
        final_docs = []
        for item in sorted_results[: self.k]:
            item["doc"].metadata["combined_score"] = item["score"]
            final_docs.append(item["doc"])

        return final_docs

    async def _aget_relevant_documents(
        self, chat_history: str, *, run_manager=None
    ) -> List[Document]:
        # Simple async wrapper for now
        # TODO: Implement true async calls if IO bound operations support it
        return self._get_relevant_documents(chat_history, run_manager=run_manager)
