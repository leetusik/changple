import logging  # Added logging
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
        whoosh_index_dir: str = "chatbot/data/whoosh_index",
        alpha: float = 0.5,
        k: int = 3,
        keyword_model: str = "gpt-4o-mini",  # llm for keyword extraction
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
            "당신은 BM25 검색에 적합한 키워드 추출 전문가입니다."
            "다음 문장에서 질문의 의도를 가장 잘 나타내는 중요한 BM25 검색용 키워드를 2개 이내로 추출하세요."
            "단, '창업', '사업', '방법', '조언' 이라는 키워드는 제외하고 출력하세요."
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
        except Exception as e:  # return original query if error occurs
            logger.error(f"Error occurred during keyword extraction: {str(e)}")
            return query

    def _get_relevant_documents(
        self, query: str, *, run_manager=None
    ) -> List[Document]:

        # Reset results for this query
        self.vector_results = []
        self.bm25_results = []

        MULTIPLIER = 5

        # vector search
        try:
            self.vector_results = (
                self.vectorstore.vectorstore.similarity_search_with_relevance_scores(
                    query, k=self.k * MULTIPLIER
                )
            )
            logger.info(f"Vector search found {len(self.vector_results)} results.")
        except Exception as e:
            logger.error(f"Error during vector search: {e}")
            self.vector_results = []  # Ensure it's empty on error

        # BM25 search - use keyword-converted query only if index is available
        if self.whoosh_ix:
            try:
                bm25_query = self.extract_keywords(query)
                logger.info(
                    f"BM25 keywords: '{bm25_query}'"
                )

                with self.whoosh_ix.searcher(
                    weighting=scoring.BM25F(title_B=2.0, content_B=1.0)
                ) as searcher:
                    parser = MultifieldParser(
                        ["title", "content"], self.whoosh_ix.schema
                    )

                    # Try AND search first
                    whoosh_query_and = parser.parse(f"({bm25_query})")
                    logger.info(f"Whoosh AND 쿼리: {whoosh_query_and}")
                    whoosh_results = searcher.search(
                        whoosh_query_and, limit=self.k * MULTIPLIER
                    )

                    # if results are less than half of k *and* there are multiple keywords, use OR search
                    if len(whoosh_results) < self.k * 0.5 and " " in bm25_query.strip():
                        logger.info(
                            f"AND 검색 결과 부족 ({len(whoosh_results)}개). OR 검색으로 전환"
                        )
                        whoosh_query_or = parser.parse(" OR ".join(bm25_query.split()))
                        logger.info(f"Whoosh OR 쿼리: {whoosh_query_or}")
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
                    logger.info(f"BM25 search found {len(self.bm25_results)} results.")
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
                            logger.warning(
                                f"Could not convert vector doc post_id '{post_id_val}' to int/string."
                            )

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
                        logger.warning(
                            f"Skipping vector doc due to missing or invalid post_id: {doc.metadata}"
                        )

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
                        logger.warning(
                            f"Could not convert vector doc post_id '{post_id_val}' to int/string."
                        )

                if doc_id:  # Only process if doc_id exists and is valid string
                    combined_scores[doc_id] = {
                        "doc": doc,
                        "score": self.alpha * 1,  # single score is normalized to 1
                    }
                else:
                    logger.warning(
                        f"Skipping vector doc due to missing or invalid post_id: {doc.metadata}"
                    )

        # BM25 results
        logger.info(
            f"BM25 search document count (before combining): {len(self.bm25_results)}"
        )
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
                        # This case should ideally not happen if Whoosh schema enforces post_id
                        logger.warning(
                            f"Skipping BM25 doc due to missing post_id: {doc.metadata}"
                        )

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
                    logger.warning(
                        f"Skipping BM25 doc due to missing post_id: {doc.metadata}"
                    )

        # final results
        sorted_results = sorted(
            combined_scores.values(), key=lambda x: x["score"], reverse=True
        )

        # save final score to metadata
        final_docs = []
        for item in sorted_results[: self.k]:
            item["doc"].metadata["combined_score"] = item["score"]
            final_docs.append(item["doc"])

        logger.info(f"Hybrid search returning {len(final_docs)} documents.")
        return final_docs

    async def _aget_relevant_documents(
        self, query: str, *, run_manager=None
    ) -> List[Document]:
        # Simple async wrapper for now
        # TODO: Implement true async calls if IO bound operations support it
        logger.warning("Using synchronous implementation for async retrieval.")
        return self._get_relevant_documents(query, run_manager=run_manager)
