"""
고급 검색 서비스 - 하이브리드 검색(벡터 검색 + 키워드 검색) 구현
벡터 검색: Pinecone을 사용한 의미적 검색(Semantic Search)
키워드 검색: OpenSearch를 사용한 BM25 알고리즘 기반 검색
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from dotenv import load_dotenv
from django.conf import settings
from datetime import datetime
from opensearchpy import OpenSearch, helpers
from chatbot.services.pinecone_service import PineconeService
from scraper.models import NaverCafeData, AllowedCategory, AllowedAuthor

# .env 파일 로드
load_dotenv()

class AdvancedRetrievalService:
    """
    하이브리드 검색 서비스 클래스 - 벡터 검색과 BM25 기반 키워드 검색을 결합
    """
    def __init__(self):
        # Pinecone 서비스 초기화 (기존 서비스 재사용)
        self.pinecone_service = PineconeService()
        
        # OpenSearch 설정
        self.opensearch_host = os.environ.get("OPENSEARCH_HOST", "localhost")
        self.opensearch_port = int(os.environ.get("OPENSEARCH_PORT", 9200))
        self.opensearch_index = os.environ.get("OPENSEARCH_INDEX", "naver_cafe_data")
        self.opensearch_user = os.environ.get("OPENSEARCH_USER", "admin")
        self.opensearch_password = os.environ.get("OPENSEARCH_PASSWORD", "admin")
        
        # OpenSearch 클라이언트 초기화
        self.opensearch_client = OpenSearch(
            hosts=[{'host': self.opensearch_host, 'port': self.opensearch_port}],
            http_auth=(self.opensearch_user, self.opensearch_password),
            use_ssl=True,
            verify_certs=False,
            ssl_show_warn=False
        )
        
        # OpenSearch 인덱스 초기화
        self._initialize_opensearch_index()
    
    def _initialize_opensearch_index(self):
        """OpenSearch 인덱스 초기화 및 매핑 설정"""
        # 인덱스가 존재하는지 확인
        if not self.opensearch_client.indices.exists(index=self.opensearch_index):
            # 인덱스 매핑 설정 - BM25 검색을 위한 필드 정의
            index_body = {
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 1,
                        # BM25 알고리즘 설정 (k1, b 파라미터 조정 가능)
                        "similarity": {
                            "default": {
                                "type": "BM25",
                                "k1": 1.2,  # 단어 빈도 가중치 (1.2~2.0 권장)
                                "b": 0.75   # 문서 길이 정규화 (0.75 권장)
                            }
                        }
                    },
                    "analysis": {
                        "analyzer": {
                            "korean": {
                                "type": "nori",  # 한국어 분석기 (nori) 사용
                                "tokenizer": "nori_tokenizer"
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "title": {
                            "type": "text",
                            "analyzer": "korean",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        "content": {
                            "type": "text",
                            "analyzer": "korean"
                        },
                        "category": {"type": "keyword"},
                        "author": {"type": "keyword"},
                        "published_date": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis"},
                        "url": {"type": "keyword"},
                        "post_id": {"type": "integer"}
                    }
                }
            }
            
            # 인덱스 생성
            self.opensearch_client.indices.create(
                index=self.opensearch_index,
                body=index_body
            )
            print(f"OpenSearch 인덱스 '{self.opensearch_index}' 생성 완료")
    
    def index_unindexed_data(self):
        """
        NaverCafeData 모델에서 아직 OpenSearch에 인덱스되지 않은 데이터를 가져와
        인덱싱합니다. 이 메서드는 vectorized=True인 데이터만 인덱싱합니다.
        (Pinecone에 이미 벡터화된 데이터만 OpenSearch에도 추가)
        """
        try:
            print("OpenSearch 인덱싱 작업을 시작합니다...")
            
            # 허용된 카테고리와 저자 목록 가져오기
            allowed_categories = list(AllowedCategory.objects.filter(is_active=True).values_list('name', flat=True))
            allowed_authors = list(AllowedAuthor.objects.filter(is_active=True).values_list('name', flat=True))
            
            # vectorized=True이고 허용된 카테고리 및 저자인 데이터만 쿼리
            # OpenSearch에 인덱싱할 때는 이미 벡터화된 데이터만 사용
            query = NaverCafeData.objects.filter(
                vectorized=True,
                category__in=allowed_categories,
                author__in=allowed_authors
            )
            
            total_documents = query.count()
            print(f"총 {total_documents}개의 문서를 OpenSearch에 인덱싱합니다.")
            
            if total_documents == 0:
                print("인덱싱할 문서가 없습니다.")
                return 0
            
            # OpenSearch 벌크 인덱싱 준비
            actions = []
            
            # 각 문서를 OpenSearch 액션으로 변환
            for i, cafe_data in enumerate(query):
                # 진행 상황 표시 (10% 단위로)
                if i % max(1, total_documents // 10) == 0 or i == total_documents - 1:
                    progress = (i / total_documents) * 100
                    print(f"진행 중... {progress:.1f}% 완료 ({i}/{total_documents})")
                
                # 날짜 포맷 변환 시도
                try:
                    if cafe_data.published_date:
                        published_date = cafe_data.published_date
                    else:
                        published_date = None
                except:
                    published_date = None
                
                # OpenSearch 문서 구조
                doc = {
                    '_index': self.opensearch_index,
                    '_id': str(cafe_data.id),  # Django ID를 OpenSearch ID로 사용
                    '_source': {
                        'id': cafe_data.id,
                        'title': cafe_data.title,
                        'content': cafe_data.content,
                        'category': cafe_data.category,
                        'author': cafe_data.author,
                        'published_date': published_date,
                        'url': cafe_data.url,
                        'post_id': cafe_data.post_id
                    }
                }
                
                actions.append(doc)
                
                # 1000개씩 벌크 인덱싱
                if len(actions) >= 1000:
                    helpers.bulk(self.opensearch_client, actions)
                    actions = []
            
            # 남은 문서 처리
            if actions:
                helpers.bulk(self.opensearch_client, actions)
            
            # 인덱스 refresh
            self.opensearch_client.indices.refresh(index=self.opensearch_index)
            
            print(f"OpenSearch 인덱싱 작업 완료! 총 {total_documents}개의 문서가 인덱싱되었습니다.")
            return total_documents
            
        except Exception as e:
            print(f"OpenSearch 인덱싱 오류: {e}")
            return 0
    
    def bm25_search(self, query_text: str, top_k: int = 5, 
                    filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        BM25 알고리즘을 사용한 키워드 검색을 수행합니다.
        
        Args:
            query_text: 검색할 쿼리 텍스트
            top_k: 반환할 최대 문서 수
            filter_dict: 검색 결과를 필터링할 조건 (예: {"category": "창플지기_칼럼"})
            
        Returns:
            list: BM25 검색 결과 (점수 포함)
        """
        try:
            # 검색 쿼리 구성
            search_query = {
                "size": top_k,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query_text,
                                    "fields": ["title^2", "content"],  # 제목에 가중치 2배
                                    "type": "best_fields"
                                }
                            }
                        ]
                    }
                },
                "highlight": {
                    "fields": {
                        "title": {"number_of_fragments": 1},
                        "content": {"number_of_fragments": 3, "fragment_size": 150}
                    },
                    "pre_tags": ["<b>"],
                    "post_tags": ["</b>"]
                }
            }
            
            # 필터 적용
            if filter_dict:
                filter_conditions = []
                for key, value in filter_dict.items():
                    if isinstance(value, list):
                        filter_conditions.append({"terms": {key: value}})
                    else:
                        filter_conditions.append({"term": {key: value}})
                
                search_query["query"]["bool"]["filter"] = filter_conditions
            
            # 검색 실행
            response = self.opensearch_client.search(
                body=search_query,
                index=self.opensearch_index
            )
            
            # 결과 포맷팅
            results = []
            for hit in response["hits"]["hits"]:
                # 하이라이트 추출
                highlights = ""
                if "highlight" in hit:
                    for field, fragments in hit["highlight"].items():
                        highlights += f"{' '.join(fragments)} "
                
                # 결과 구성
                result = {
                    'id': hit["_source"]["id"],
                    'content': hit["_source"]["content"],
                    'metadata': {
                        'document_id': hit["_source"]["id"],
                        'title': hit["_source"]["title"],
                        'category': hit["_source"]["category"],
                        'author': hit["_source"]["author"],
                        'upload_date': hit["_source"].get("published_date", ""),
                        'url': hit["_source"]["url"],
                        'post_id': hit["_source"]["post_id"]
                    },
                    'highlights': highlights,
                    'bm25_score': hit["_score"]
                }
                results.append(result)
                
            return results
            
        except Exception as e:
            print(f"BM25 검색 오류: {e}")
            return []
    
    def hybrid_search(self, query_text: str, top_k: int = 5, 
                      filter_dict: Optional[Dict[str, Any]] = None,
                      vector_weight: float = 0.5) -> List[Dict[str, Any]]:
        """
        벡터 검색(의미 기반)과 BM25 검색(키워드 기반)을 결합한 하이브리드 검색을 수행합니다.
        
        Args:
            query_text: 검색할 쿼리 텍스트
            top_k: 반환할 최대 문서 수
            filter_dict: 검색 결과를 필터링할 조건
            vector_weight: 벡터 검색 결과 가중치 (0.0 ~ 1.0)
                           1.0은 벡터 검색만, 0.0은 BM25 검색만 사용
            
        Returns:
            list: 하이브리드 검색 결과
        """
        # 가중치 검증
        if vector_weight < 0 or vector_weight > 1:
            vector_weight = 0.5
        
        # 검색 결과를 위한 top_k 확장 (각 검색에서 더 많은 결과를 가져와 최종 결과에서 top_k 선택)
        expanded_k = min(top_k * 3, 50)  # 최대 50개 제한
        
        # 1. 벡터 검색 수행 (Pinecone)
        vector_results = self.pinecone_service.search_similar_documents(
            query_text, 
            top_k=expanded_k,
            filter_dict=filter_dict
        )
        
        # 2. BM25 검색 수행 (OpenSearch)
        bm25_results = self.bm25_search(
            query_text,
            top_k=expanded_k,
            filter_dict=filter_dict
        )
        
        # 3. 결과 병합 및 점수 정규화
        # - 각 검색의 최대 점수를 찾아 정규화
        max_vector_score = max([result.get('similarity_score', 0) for result in vector_results]) if vector_results else 1
        max_bm25_score = max([result.get('bm25_score', 0) for result in bm25_results]) if bm25_results else 1
        
        # 문서 ID별 결과 맵 생성
        result_map = {}
        
        # 벡터 검색 결과 처리
        for result in vector_results:
            doc_id = result['metadata'].get('document_id')
            
            # 정규화된 점수 계산
            normalized_score = result.get('similarity_score', 0) / max_vector_score if max_vector_score > 0 else 0
            
            result_map[doc_id] = {
                'content': result['content'],
                'metadata': result['metadata'],
                'vector_score': result.get('similarity_score', 0),
                'normalized_vector_score': normalized_score,
                'bm25_score': 0,
                'normalized_bm25_score': 0,
                'hybrid_score': normalized_score * vector_weight
            }
        
        # BM25 검색 결과 처리
        for result in bm25_results:
            doc_id = result['metadata'].get('document_id')
            
            # 정규화된 점수 계산
            normalized_score = result.get('bm25_score', 0) / max_bm25_score if max_bm25_score > 0 else 0
            
            if doc_id in result_map:
                # 기존 결과에 BM25 점수 추가
                result_map[doc_id]['bm25_score'] = result.get('bm25_score', 0)
                result_map[doc_id]['normalized_bm25_score'] = normalized_score
                result_map[doc_id]['highlights'] = result.get('highlights', '')
                # 하이브리드 점수 계산 (가중치 적용)
                result_map[doc_id]['hybrid_score'] += normalized_score * (1 - vector_weight)
            else:
                # 새 결과 추가
                result_map[doc_id] = {
                    'content': result['content'],
                    'metadata': result['metadata'],
                    'highlights': result.get('highlights', ''),
                    'vector_score': 0,
                    'normalized_vector_score': 0,
                    'bm25_score': result.get('bm25_score', 0),
                    'normalized_bm25_score': normalized_score,
                    'hybrid_score': normalized_score * (1 - vector_weight)
                }
        
        # 하이브리드 점수로 정렬된 결과 생성
        merged_results = sorted(
            result_map.values(), 
            key=lambda x: x['hybrid_score'], 
            reverse=True
        )
        
        # top_k개 결과만 반환
        return merged_results[:top_k]
    
    def get_retriever(self, search_type: str = "hybrid", 
                      vector_weight: float = 0.5) -> Any:
        """
        LangChain과 통합하기 위한 retriever 객체를 반환합니다.
        이 메서드는 검색 유형에 따라 다른 retriever를 반환합니다.
        
        Args:
            search_type: 검색 유형 ("hybrid", "vector", "bm25")
            vector_weight: 하이브리드 검색에서 벡터 검색의 가중치
            
        Returns:
            retriever: LangChain과 통합할 수 있는 retriever 객체
        """
        from langchain.schema import BaseRetriever, Document
        from langchain.callbacks.manager import CallbackManagerForRetrieverRun
        from pydantic import BaseModel, Field

        # 하이브리드 retriever 클래스 정의
        class HybridRetriever(BaseRetriever, BaseModel):
            service: Any = Field(default=self)
            search_type: str = Field(default=search_type)
            top_k: int = Field(default=5)
            vector_weight: float = Field(default=vector_weight)
            
            class Config:
                arbitrary_types_allowed = True
            
            def _get_relevant_documents(
                self, query: str, *, run_manager: CallbackManagerForRetrieverRun
            ) -> List[Document]:
                if self.search_type == "hybrid":
                    results = self.service.hybrid_search(
                        query, 
                        top_k=self.top_k, 
                        vector_weight=self.vector_weight
                    )
                elif self.search_type == "vector":
                    results = self.service.pinecone_service.search_similar_documents(
                        query, 
                        top_k=self.top_k
                    )
                elif self.search_type == "bm25":
                    results = self.service.bm25_search(
                        query, 
                        top_k=self.top_k
                    )
                else:
                    # 기본값은 하이브리드 검색
                    results = self.service.hybrid_search(
                        query, 
                        top_k=self.top_k, 
                        vector_weight=self.vector_weight
                    )
                
                # 검색 결과를 LangChain Document 형식으로 변환
                documents = []
                for result in results:
                    # 검색 유형에 따라 점수 추출
                    if self.search_type == "hybrid":
                        score = result.get('hybrid_score', 0)
                    elif self.search_type == "vector":
                        score = result.get('similarity_score', 0)
                    else:  # bm25
                        score = result.get('bm25_score', 0)
                    
                    # 메타데이터 준비
                    metadata = result['metadata'].copy()
                    metadata['score'] = score
                    
                    # 하이라이트 정보가 있으면 추가
                    if 'highlights' in result:
                        metadata['highlights'] = result['highlights']
                    
                    # Document 객체 생성
                    doc = Document(
                        page_content=result['content'],
                        metadata=metadata
                    )
                    documents.append(doc)
                
                return documents
        
        # retriever 객체 반환
        return HybridRetriever(
            service=self,
            search_type=search_type,
            vector_weight=vector_weight
        )
    
    def clear_opensearch_index(self) -> bool:
        """
        OpenSearch 인덱스의 모든 문서를 삭제합니다.
        
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            if self.opensearch_client.indices.exists(index=self.opensearch_index):
                self.opensearch_client.indices.delete(index=self.opensearch_index)
                # 인덱스 재생성
                self._initialize_opensearch_index()
                return True
            return False
        except Exception as e:
            print(f"OpenSearch 인덱스 초기화 오류: {e}")
            return False
