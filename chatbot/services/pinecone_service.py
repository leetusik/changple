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
from scraper.models import NaverCafeData, AllowedCategory, AllowedAuthor
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
            chunk_size=getattr(settings, "TEXT_SPLITTER_CHUNK_SIZE", 1000),
            chunk_overlap=getattr(settings, "TEXT_SPLITTER_CHUNK_OVERLAP", 100),
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
        # .env 파일에서 인덱스 이름 가져오기
        index_name = os.environ.get("PINECONE_INDEX_NAME")
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
    
    def process_cafe_data(self, start_post_id=None, num_document=None):
        """
        NaverCafeData 모델에서 데이터를 가져와 Pinecone에 저장합니다.
        
        Args:
            start_post_id: 조회 시작할 post_id (이 값보다 크거나 같은 post_id부터 조회)
            num_document: 처리할 문서 수, 없으면 전체 문서 처리 (e.g. 1000)
        
        Returns:
            int: 생성된 총 청크 수
        """
        try:
            print(f"카페 데이터 인덱싱 작업을 시작합니다...")
            
            # 쿼리 구성
            query = NaverCafeData.objects.all()
            
            if start_post_id:
                query = query.filter(post_id__gte=start_post_id)
            
            if num_document:
                query = query[:num_document]
            
            total_documents = query.count()
            print(f"총 {total_documents}개의 문서를 처리합니다.")
            
            # 문서 처리 및 벡터 저장 준비
            documents = []
            chunk_counters = {}  # 각 post_id별 청크 카운터를 추적하기 위한 딕셔너리
            
            for i, cafe_data in enumerate(query):
                # 진행 상황 표시 (10% 단위로)
                if i % max(1, total_documents // 10) == 0 or i == total_documents - 1:
                    progress = (i / total_documents) * 100
                    print(f"진행 중... {progress:.1f}% 완료 ({i}/{total_documents})")
                
                # 텍스트 분할
                chunks = self.text_splitter.split_text(cafe_data.content)
                post_id = cafe_data.post_id
                
                # 이 post_id에 대한 카운터 초기화
                if post_id not in chunk_counters:
                    chunk_counters[post_id] = 1
                
                # 각 청크에 대한 메타데이터 생성
                for chunk in chunks:
                    metadata = {
                        'document_id': cafe_data.id,
                        'title': cafe_data.title,
                        'category': cafe_data.category,
                        'upload_date': cafe_data.published_date.isoformat() if cafe_data.published_date else '',
                        'author': cafe_data.author,
                        'url': cafe_data.url,
                        'post_id': post_id,
                        'chunk_number': chunk_counters[post_id],  # 청크 번호 저장
                    }
                    documents.append((chunk, metadata, chunk_counters[post_id]))
                    chunk_counters[post_id] += 1  # 다음 청크를 위해 카운터 증가
            
            if not documents:
                print("인덱싱할 문서가 없습니다.")
                return 0
            
            # 벡터 저장소에 문서 추가 (배치 처리)
            batch_size = 100
            total_batches = (len(documents) + batch_size - 1) // batch_size
            
            print(f"총 {len(documents)}개의 청크를 {total_batches}개 배치로 처리합니다.")
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                batch_num = i // batch_size + 1
                
                print(f"배치 처리 중... {batch_num}/{total_batches} ({(batch_num/total_batches)*100:.1f}%)")
                
                texts = [doc[0] for doc in batch]
                metadatas = [doc[1] for doc in batch]
                
                # 각 청크에 post_id와 chunk_number를 조합하여 고유 ID 생성
                ids = [f"{meta['post_id']}-{doc[2]}" for meta, doc in zip(metadatas, batch)]
                
                # ID를 명시적으로 지정하여 업서트 (동일 ID는 덮어쓰기됨)
                self.vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)
            
            # 총 청크 수 계산 (각 post_id의 마지막 청크 번호 - 1을 합산)
            # chunk_counters의 각 값은 마지막 청크 번호 + 1이므로 1을 빼지 않음
            total_chunks = sum(chunk_counters.values()) - len(chunk_counters)
            
            print(f"인덱싱 작업 완료! 총 {total_chunks}개의 청크가 생성되었습니다.")
            return total_chunks
            
        except Exception as e:
            print(f"Pinecone 처리 오류: {e}")
            return 0
        
    def process_unvectorized_data(self):
        """
        NaverCafeData 모델에서 vectorized=False이고 허용된 카테고리 및 저자의 데이터만 가져와 
        Pinecone에 저장합니다. 처리 후 해당 데이터의 vectorized 필드를 True로 업데이트합니다.
        
        Returns:
            int: 생성된 총 청크 수
        """
        try:
            print(f"벡터화되지 않은 카페 데이터 인덱싱 작업을 시작합니다...")
            
            # 허용된 카테고리와 저자 목록 가져오기
            allowed_categories = list(AllowedCategory.objects.filter(is_active=True).values_list('name', flat=True))
            allowed_authors = list(AllowedAuthor.objects.filter(is_active=True).values_list('name', flat=True))
            
            print(f"허용된 카테고리 수: {len(allowed_categories)}, 허용된 저자 수: {len(allowed_authors)}")
            
            # vectorized=False, 허용된 카테고리 및 저자인 데이터만 쿼리
            query = NaverCafeData.objects.filter(
                vectorized=False,
                category__in=allowed_categories,
                author__in=allowed_authors
            )
            
            total_documents = query.count()
            print(f"총 {total_documents}개의 미벡터화 문서를 처리합니다.")
            
            input("Press Enter to continue...")
            if total_documents == 0:
                print("벡터화할 새 문서가 없습니다.")
                return 0
            
            # 문서 처리 및 벡터 저장 준비
            documents = []
            chunk_counters = {}  # 각 post_id별 청크 카운터를 추적하기 위한 딕셔너리
            processed_document_ids = []  # 처리된 문서 ID를 저장할 리스트
            
            for i, cafe_data in enumerate(query):
                # 진행 상황 표시 (10% 단위로)
                if i % max(1, total_documents // 10) == 0 or i == total_documents - 1:
                    progress = (i / total_documents) * 100
                    print(f"진행 중... {progress:.1f}% 완료 ({i}/{total_documents})")
                
                # 텍스트 분할
                chunks = self.text_splitter.split_text(cafe_data.content)
                post_id = cafe_data.post_id
                
                # 이 post_id에 대한 카운터 초기화
                if post_id not in chunk_counters:
                    chunk_counters[post_id] = 1
                
                # 각 청크에 대한 메타데이터 생성
                for chunk in chunks:
                    metadata = {
                        'document_id': cafe_data.id,
                        'title': cafe_data.title,
                        'category': cafe_data.category,
                        'upload_date': cafe_data.published_date.isoformat() if cafe_data.published_date else '',
                        'author': cafe_data.author,
                        'url': cafe_data.url,
                        'post_id': post_id,
                        'chunk_number': chunk_counters[post_id],  # 청크 번호 저장
                    }
                    documents.append((chunk, metadata, chunk_counters[post_id]))
                    chunk_counters[post_id] += 1  # 다음 청크를 위해 카운터 증가
                
                # 처리된 문서 ID 저장
                processed_document_ids.append(cafe_data.id)
            
            if not documents:
                print("인덱싱할 문서가 없습니다.")
                return 0
            
            # 벡터 저장소에 문서 추가 (배치 처리)
            batch_size = 100
            total_batches = (len(documents) + batch_size - 1) // batch_size
            
            print(f"총 {len(documents)}개의 청크를 {total_batches}개 배치로 처리합니다.")
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                batch_num = i // batch_size + 1
                
                print(f"배치 처리 중... {batch_num}/{total_batches} ({(batch_num/total_batches)*100:.1f}%)")
                
                texts = [doc[0] for doc in batch]
                metadatas = [doc[1] for doc in batch]
                
                # 각 청크에 post_id와 chunk_number를 조합하여 고유 ID 생성
                ids = [f"{meta['post_id']}-{doc[2]}" for meta, doc in zip(metadatas, batch)]
                
                # ID를 명시적으로 지정하여 업서트 (동일 ID는 덮어쓰기됨)
                self.vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)
            
            # 총 청크 수 계산 (각 post_id의 마지막 청크 번호 - 1을 합산)
            # chunk_counters의 각 값은 마지막 청크 번호 + 1이므로 1을 빼지 않음
            total_chunks = sum(chunk_counters.values()) - len(chunk_counters)
            
            # 처리된 문서의 vectorized 필드를 True로 업데이트
            NaverCafeData.objects.filter(id__in=processed_document_ids).update(vectorized=True)
            
            print(f"인덱싱 작업 완료! 총 {total_chunks}개의 청크가 생성되었습니다.")
            print(f"{len(processed_document_ids)}개 문서의 vectorized 상태가 True로 업데이트되었습니다.")
            return total_chunks
            
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
    
    def get_stats(self, vectorized=None, allowed_category_active=None, allowed_author_active=None) -> Dict[str, Any]:
        """
        처리된 문서 통계 정보를 반환합니다.
        
        Args:
            vectorized: 벡터화 상태로 필터링 (None=모두, True=벡터화됨, False=벡터화안됨)
            allowed_category_active: 허용된 카테고리 활성화 상태로 필터링 (None=모두, True=활성화된 카테고리, False=비활성화된 카테고리)
            allowed_author_active: 허용된 저자 활성화 상태로 필터링 (None=모두, True=활성화된 저자, False=비활성화된 저자)
        
        Returns:
            Dict: 통계 정보
        """
        try:
            # 필터 조건 준비
            query_filter = {}
            
            # 벡터화 상태에 따른 필터링
            if vectorized is not None:
                query_filter['vectorized'] = vectorized
            
            # 허용된 카테고리 상태에 따른 필터링
            if allowed_category_active is not None:
                allowed_categories = AllowedCategory.objects.filter(is_active=allowed_category_active).values_list('name', flat=True)
                query_filter['category__in'] = allowed_categories
            
            # 허용된 저자 상태에 따른 필터링
            if allowed_author_active is not None:
                allowed_authors = AllowedAuthor.objects.filter(is_active=allowed_author_active).values_list('name', flat=True)
                query_filter['author__in'] = allowed_authors
            
            # 필터 조건 적용
            cafe_data_query = NaverCafeData.objects.filter(**query_filter)
            
            # Django ORM으로 통계 정보 조회
            django_total_documents = cafe_data_query.count()
            
            # 필터 상태를 결과에 포함
            filter_status = {
                '벡터화 상태 필터': '전체' if vectorized is None else ('벡터화됨' if vectorized else '벡터화안됨'),
                '허용 카테고리 필터': '전체' if allowed_category_active is None else ('활성화됨' if allowed_category_active else '비활성화됨'),
                '허용 저자 필터': '전체' if allowed_author_active is None else ('활성화됨' if allowed_author_active else '비활성화됨')
            }
            
            # 카테고리별 문서 수 
            category_counts = cafe_data_query.values('category').annotate(
                count=Count('id')
            ).order_by('-count')
            category_stats = {item['category']: item['count'] for item in category_counts}
            
            # 저자별 문서 수
            author_counts = cafe_data_query.values('author').annotate(
                count=Count('id')
            ).order_by('-count')
            author_stats = {item['author']: item['count'] for item in author_counts}
            
            # post_id 분포도 분석
            min_post_id = cafe_data_query.order_by('post_id').values_list('post_id', flat=True).first() or 0
            max_post_id = cafe_data_query.order_by('-post_id').values_list('post_id', flat=True).first() or 0
            
            # post_id 범위를 10개 구간으로 나누어 분포 확인
            if min_post_id < max_post_id:
                range_size = (max_post_id - min_post_id) // 10
                if range_size < 1:
                    range_size = 1
                
                post_id_distribution = {}
                for i in range(10):
                    start_range = min_post_id + (i * range_size)
                    end_range = min_post_id + ((i + 1) * range_size) if i < 9 else max_post_id + 1
                    
                    count = cafe_data_query.filter(
                        post_id__gte=start_range, 
                        post_id__lt=end_range
                    ).count()
                    
                    post_id_distribution[f"{start_range}~{end_range-1}"] = count
            else:
                post_id_distribution = {"데이터 없음": 0}
  
            # Pinecone 인덱스 통계
            index_stats = self.index.describe_index_stats()
            vector_count = index_stats.get('total_vector_count', 0)
            
            return {
                '[ Pinecone vector 수 ]': vector_count,
                '[ Django_documents 수 ]': django_total_documents,
                '[ 필터 상태 ]': filter_status,
                '[ post_id 범위 ]': f"{min_post_id} ~ {max_post_id}",
                '[ post_id 분포도 ]': post_id_distribution,
                '카테고리별 documents 수': category_stats,
                '저자별 documents 수': author_stats
            }
            
        except Exception as e:
            print(f"통계 조회 오류: {e}")
            return {
                'error': str(e)
            } 