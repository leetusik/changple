"""
Pinecone service for the chatbot application.
This module contains functionality for Pinecone vector database integration.
"""

# Import necessary libraries
import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Pinecone as LangchainPinecone
from django.utils import timezone
from django.conf import settings
from scraper.models import NaverCafeData
from django.db.models import Count
from typing import List, Dict, Any, Optional
from datetime import datetime

# .env 파일 로드
load_dotenv()

class PineconeService:
    """
    Service for handling Pinecone vector database functionality.
    """
    def __init__(self, api_key=None, environment=None, index_name=None):
        # Initialize Pinecone components
        self.api_key = api_key or self._get_api_key_from_env()
        self.environment = environment or self._get_environment_from_env()
        self.index_name = index_name or self._get_index_name_from_env()
        
        # 임베딩 및 텍스트 분할 설정
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len
        )
        
        # Pinecone 초기화
        self._initialize_pinecone()
    
    def _get_api_key_from_env(self):
        # .env 파일에서 API 키 가져오기
        api_key = os.environ.get("PINECONE_API_KEY")
        # 환경 변수에 없으면 Django settings에서 가져오기 (폴백 메커니즘)
        if not api_key:
            api_key = getattr(settings, "PINECONE_API_KEY", None)
        return api_key
    
    def _get_environment_from_env(self):
        # .env 파일에서 환경 가져오기
        environment = os.environ.get("PINECONE_ENVIRONMENT")
        # 환경 변수에 없으면 Django settings에서 가져오기, 기본값은 "us-east-1"
        if not environment:
            environment = getattr(settings, "PINECONE_ENVIRONMENT", "us-east-1")
        return environment
    
    def _get_index_name_from_env(self):
        # Django settings에서 인덱스 이름 가져오기,
        index_name = getattr(settings, "PINECONE_INDEX_NAME", "pdf-index")
        return index_name
    
    def _initialize_pinecone(self):
        """Pinecone 클라이언트 초기화 및 인덱스 생성"""
        try:
            # Pinecone 클라이언트 초기화
            self.pc = Pinecone(api_key=self.api_key)
            
            # 인덱스 존재 확인과 생성
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            if self.index_name not in existing_indexes:
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1536,  # OpenAI 임베딩 차원
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=self.environment)
                )
                print(f"인덱스 '{self.index_name}' 생성됨")
            
            # 인덱스 연결
            self.index = self.pc.Index(self.index_name)
            
            # LangChain 벡터스토어 연결
            self.vectorstore = LangchainPinecone.from_existing_index(
                index_name=self.index_name,
                embedding=self.embeddings
            )
        except Exception as e:
            print(f"Pinecone 초기화 오류: {e}")
            raise
    
    def process_cafe_data(self, start_date=None, end_date=None, limit=None):
        """
        NaverCafeData 모델에서 데이터를 가져와 Pinecone에 저장합니다.
        
        Args:
            start_date: 조회 시작 날짜 (e.g. "2025-01-01", datetime 객체)
            end_date: 조회 종료 날짜 (e.g. "2025-01-31", datetime 객체)
            limit: 최대 처리할 문서 수, 없으면 전체 문서 처리 (e.g. 1000)
        
        Returns:
            int: 처리된 문서 청크 수
        """
        try:
            # 쿼리 구성
            query = NaverCafeData.objects.all()
            
            if start_date:
                if isinstance(start_date, str):
                    # 문자열인 경우 datetime으로 변환 후 timezone 정보 추가
                    start_datetime = timezone.make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
                elif timezone.is_naive(start_date):
                    # naive datetime인 경우 timezone 정보 추가
                    start_datetime = timezone.make_aware(start_date)
                else:
                    # 이미 timezone 정보가 있는 경우 그대로 사용
                    start_datetime = start_date
                
                query = query.filter(published_date__gte=start_datetime)
            
            if end_date:
                if isinstance(end_date, str):
                    # 문자열인 경우 datetime으로 변환 후 timezone 정보 추가
                    end_datetime = timezone.make_aware(datetime.strptime(end_date, "%Y-%m-%d"))
                elif timezone.is_naive(end_date):
                    # naive datetime인 경우 timezone 정보 추가
                    end_datetime = timezone.make_aware(end_date)
                else:
                    # 이미 timezone 정보가 있는 경우 그대로 사용
                    end_datetime = end_date
                
                query = query.filter(published_date__lte=end_datetime)
            
            if limit:
                query = query[:limit]
            
            # 문서 처리 및 벡터 저장 준비
            documents = []
            
            for cafe_data in query:
                # 텍스트 분할
                chunks = self.text_splitter.split_text(cafe_data.content)
                
                # 각 청크에 대한 메타데이터 생성
                for chunk in chunks:
                    metadata = {
                        'document_id': cafe_data.id,
                        'title': cafe_data.title,
                        'category': cafe_data.category,
                        'upload_date': cafe_data.published_date.isoformat() if cafe_data.published_date else '',
                        'author': cafe_data.author,
                        'url': cafe_data.url,
                        'post_id': cafe_data.post_id,
                    }
                    documents.append((chunk, metadata))
            
            if not documents:
                return 0
            
            # 벡터 저장소에 문서 추가 (배치 처리)
            batch_size = 100
            total_processed = 0
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                
                texts = [doc[0] for doc in batch]
                metadatas = [doc[1] for doc in batch]
                
                # 각 청크에 고유 ID 생성 (post_id와 청크 인덱스 조합)
                ids = [f"{meta['post_id']}-{total_processed+j}" for j, meta in enumerate(metadatas)]
                
                # ID를 명시적으로 지정하여 업서트 (동일 ID는 덮어쓰기됨)
                self.vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)
                
                total_processed += len(batch)
            
            return total_processed
            
        except Exception as e:
            print(f"Pinecone 처리 오류: {e}")
            return 0
    
    def search_similar_documents(self, query_text: str, top_k: int = 5, 
                                filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        임베딩 기반 유사 문서 검색
        
        Args:
            query_text: 검색할 쿼리 텍스트
            top_k: 반환할 최대 문서 수
            filter_dict: 검색 결과를 필터링할 메타데이터 조건 (예: {"category": "창플지기_칼럼"})
            
        Returns:
            list: 유사도 점수와 문서 정보가 포함된 결과 리스트
        """
        try:
            results = self.vectorstore.similarity_search_with_score(
                query_text, 
                k=top_k,
                filter=filter_dict
            )
            
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'similarity_score': score
                })
                
            return formatted_results
        except Exception as e:
            print(f"문서 검색 오류: {e}")
            return []
    
    def clear_index(self) -> bool:
        """
        인덱스의 모든 벡터를 삭제합니다.
        
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            self.index.delete(delete_all=True)
            return True
        except Exception as e:
            print(f"인덱스 초기화 오류: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        처리된 문서 통계 정보를 반환합니다.
        
        Returns:
            Dict: 통계 정보
        """
        try:
            # Django ORM으로 통계 정보 조회
            django_total_documents = NaverCafeData.objects.count()
            
            # 카테고리별 문서 수 
            category_counts = NaverCafeData.objects.values('category').annotate(
                count=Count('id')
            ).order_by('-count')
            category_stats = {item['category']: item['count'] for item in category_counts}
            
            # 저자별 문서 수
            author_counts = NaverCafeData.objects.values('author').annotate(
                count=Count('id')
            ).order_by('-count')
            author_stats = {item['author']: item['count'] for item in author_counts}
  
            # Pinecone 인덱스 통계
            index_stats = self.index.describe_index_stats()
            vector_count = index_stats.get('total_vector_count', 0)
            
            return {
                '[ Pinecone vector 수 ]': vector_count,
                '[ Django_documents 수 ]': django_total_documents,
                '카테고리별 documents 수': category_stats,
                '저자별 documents 수': author_stats
            }
            
        except Exception as e:
            print(f"통계 조회 오류: {e}")
            return {
                'error': str(e)
            } 