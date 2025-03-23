from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from chatbot.services.pinecone_service import PineconeService
from chatbot.services.langchain_service import LangchainService
from chatbot.models import Prompt, ABTest
from scraper.models import NaverCafeData, AllowedCategory, AllowedAuthor
from django.conf import settings
from django.utils.text import slugify
import os
from dotenv import load_dotenv
from chatbot.services.advanced_retrieval_service import AdvancedRetrievalService

# 파일 시작 부분에 .env 로드
load_dotenv()

# Create your views here.

def index(request):
    # 메인 페이지 렌더링
    return render(request, 'index.html')

def chat_view(request):
    # 챗봇 페이지 렌더링
    return render(request, 'chat/chat.html')

def search_view(request):
    query = request.GET.get('q', '')
    return render(request, 'index.html', {'query': query})

@api_view(['POST'])
def search_documents(request):
    """문서 검색 API 엔드포인트"""
    data = request.data
    query = data.get('query', '')
    top_k = data.get('top_k', 5)
    filters = data.get('filters', None)
    
    if not query:
        return Response({"error": "검색어를 입력해주세요."}, status=400)
    
    pinecone_service = PineconeService()
    results = pinecone_service.search_similar_documents(query, top_k=top_k, filter_dict=filters)
    
    return Response({"results": results})

@api_view(['POST'])
def index_cafe_data(request):
    """카페 데이터 인덱싱 API 엔드포인트"""
    try:
        # process_cafe_data 대신 process_unvectorized_data 함수 사용
        pinecone_service = PineconeService()
        total_chunks = pinecone_service.process_unvectorized_data()
        
        return Response({
            "success": True,
            "total_chunks": total_chunks,
            "message": f"벡터화되지 않은 카페 데이터 인덱싱 완료. 총 {total_chunks}개의 청크가 생성되었습니다."
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)
    
@api_view(['POST'])
def clear_pinecone_index(request):
    """Pinecone 인덱스 초기화 API 엔드포인트"""
    try:
        pinecone_service = PineconeService()
        result = pinecone_service.clear_index()
        
        if result:
            message = "Pinecone 인덱스가 성공적으로 초기화되었습니다."
            return Response({"success": True, "message": message})
        else:
            return Response({"error": "인덱스 초기화 중 오류가 발생했습니다."}, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def get_pinecone_stats(request):
    """Pinecone 통계 정보 조회 API 엔드포인트"""
    # URL 예시: /chatbot/pinecone-stats/?vectorized=true&allowed_category=true&allowed_author=true
    # URL 쿼리 파라미터에서 필터 옵션 가져오기

    vectorized = request.query_params.get('vectorized', 'true').lower() == 'true'
    allowed_category = request.query_params.get('allowed_category', 'true').lower() == 'true'
    allowed_author = request.query_params.get('allowed_author', 'true').lower() == 'true'
    
    print(f"필터링 조건 | vectorized: {vectorized}, allowed_category: {allowed_category}, allowed_author: {allowed_author}")

    # 필터링 옵션 적용하여 통계 조회
    pinecone_service = PineconeService()
    stats = pinecone_service.get_stats(vectorized, allowed_category, allowed_author)
    
    return Response(stats)

@api_view(['POST'])
def chat(request):
    """챗봇 대화 API 엔드포인트"""
    data = request.data
    query = data.get('query', '')
    history = data.get('history', [])
    prompt_id = data.get('prompt_id', getattr(settings, 'PROMPT_ID', None))
    model = getattr(settings, 'LLM_MODEL', 'gpt-4o-mini')

    if not query:
        return Response({"error": "질문을 입력해주세요."}, status=400)

    langchain_service = LangchainService()
    response = langchain_service.generate_response(query, history, prompt_id=prompt_id, model=model)
    
    # 새 대화를 history에 추가
    updated_history = history.copy()
    
    # 사용자 질문 추가
    updated_history.append({
        "role": "user",
        "content": query
    })
    
    # AI 응답 추가
    updated_history.append({
        "role": "assistant",
        "content": response
    })
    
    return Response({
        "response": response,
        "history": updated_history  # 업데이트된 대화 이력 반환
    })

def ab_test_view(request):
    """A/B 테스트 페이지를 렌더링합니다."""
    prompts = Prompt.objects.all().order_by('-created_at')
    return render(request, 'management/ab_test.html', {'prompts': prompts})

@api_view(['POST'])
def run_ab_test(request):
    query = request.data.get('query')
    prompt_a_id = request.data.get('prompt_a')
    prompt_b_id = request.data.get('prompt_b')
    llm_model = request.data.get('llm_model', 'gpt-4o-mini')
    
    try:
        # Langchain 서비스 인스턴스 생성
        langchain_service = LangchainService()
        
        # 각 프롬프트로 응답 생성
        response_a = langchain_service.generate_response(query, prompt_id=prompt_a_id, model=llm_model)
        response_b = langchain_service.generate_response(query, prompt_id=prompt_b_id, model=llm_model)
        
        # settings에서 값 가져오기
        llm_temperature = getattr(settings, "LLM_TEMPERATURE", 0.7)
        llm_top_k = getattr(settings, "LLM_TOP_K", 5)
        chunk_size = getattr(settings, "TEXT_SPLITTER_CHUNK_SIZE", 1000)
        chunk_overlap = getattr(settings, "TEXT_SPLITTER_CHUNK_OVERLAP", 200)
        
        # 테스트 결과 저장
        test = ABTest.objects.create(
            query=query,
            prompt_a=Prompt.objects.get(id=prompt_a_id),
            prompt_b=Prompt.objects.get(id=prompt_b_id),
            response_a=response_a,
            response_b=response_b,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_top_k=llm_top_k,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        return Response({
            'test_id': test.id,
            'response_a': response_a,
            'response_b': response_b,
            'llm_model': llm_model,
            'llm_temperature': llm_temperature,
            'llm_top_k': llm_top_k,
            'chunk_size': chunk_size,
            'chunk_overlap': chunk_overlap
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
def vote_ab_test(request):
    test_id = request.data.get('test_id')
    winner = request.data.get('winner')
    
    try:
        test = ABTest.objects.get(id=test_id)
        
        # 노출 횟수 증가
        test.prompt_a.num_exposure += 1
        test.prompt_b.num_exposure += 1
        test.prompt_a.save()
        test.prompt_b.save()
        
        # winner를 문자열로 저장
        test.winner = winner
        test.save()
        
        # 승자 프롬프트 점수 증가
        if winner == 'a':
            prompt = test.prompt_a
        else:
            prompt = test.prompt_b
            
        prompt.score += 1
        prompt.save()
        
        return Response({'success': True})
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
def create_prompt(request):
    """프롬프트 생성 API 엔드포인트"""
    data = request.data
    
    try:
        prompt = Prompt.objects.create(
            name=data.get('name'),
            content=data.get('content'),
            description=data.get('description', '')
        )
        
        return Response({
            "success": True,
            "id": prompt.id,
            "message": "프롬프트가 생성되었습니다."
        })
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['PUT'])
def update_prompt(request, prompt_id):
    """프롬프트 수정 API 엔드포인트"""
    data = request.data
    
    try:
        # 이제 항상 ID로만 검색
        prompt = Prompt.objects.get(id=prompt_id)
        
        # 데이터 업데이트 - prompt_id 관련 코드 제거
        if 'name' in data:
            prompt.name = data['name']
        if 'content' in data:
            prompt.content = data['content']
        if 'description' in data:
            prompt.description = data['description']
        
        # 점수와 노출 수 필드
        if 'score' in data:
            try:
                prompt.score = int(data['score'])
            except (ValueError, TypeError):
                return Response({"error": "점수는 숫자 형식이어야 합니다."}, status=400)
                
        if 'num_exposure' in data:
            try:
                prompt.num_exposure = int(data['num_exposure'])
            except (ValueError, TypeError):
                return Response({"error": "노출 횟수는 숫자 형식이어야 합니다."}, status=400)
        
        prompt.save()
        
        return Response({
            "success": True,
            "message": f"프롬프트가 성공적으로 업데이트되었습니다."
        })
    except Prompt.DoesNotExist:
        return Response({"error": "프롬프트를 찾을 수 없습니다."}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['DELETE'])
def delete_prompt(request, prompt_id):
    """프롬프트를 삭제하는 API 엔드포인트"""
    try:
        prompt = Prompt.objects.get(id=prompt_id)
        prompt_name = prompt.name
        prompt.delete()
        
        return Response({
            "success": True,
            "message": f"프롬프트 '{prompt_name}'가 삭제되었습니다."
        })
    except Prompt.DoesNotExist:
        return Response({"error": "프롬프트를 찾을 수 없습니다."}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['GET'])
def get_prompts(request):
    """모든 프롬프트 정보를 JSON으로 반환합니다."""
    prompts = Prompt.objects.all()
    prompt_data = []
    
    for prompt in prompts:
        prompt_data.append({
            'id': prompt.id,
            'name': prompt.name,
            'description': prompt.description,
            'updated_at': prompt.updated_at.isoformat(),
            'score': prompt.score,
            'num_exposure': prompt.num_exposure
        })
    
    return Response({'prompts': prompt_data})

def api_management_view(request):
    """API 관리 페이지를 렌더링합니다."""
    apis = [
        {
            'name': '문서 검색',
            'id': 'search-documents',
            'url': '/chatbot/search/',
            'method': 'POST',
            'description': 'Pinecone에 저장된 문서를 similarity search 합니다. (상위 k개)',
            'params': {
                'query': '검색어',
                'top_k': '결과 개수',
                'filters': '필터(선택사항)'
            },
            'example_json': '''{
  "query": "카페 이용방법",
  "top_k": 5,
  "filters": {"category": "FAQ"}
}'''
        },
        {
            'name': '카페 데이터 인덱싱',
            'id': 'index-cafe-data',
            'url': '/chatbot/index-cafe-data/',
            'method': 'POST',
            'description': '아직 벡터화되지 않은(vectorized=False) 카페 데이터만 Pinecone에 저장합니다. 허용된 카테고리와 작성자의 데이터만 처리합니다.',
            'params': {},
            'example_json': ''
        },
        {
            'name': '프롬프트_생성',
            'id': 'create-prompt',
            'url': '/chatbot/create-prompt/',
            'method': 'POST',
            'description': '새 프롬프트를 Django DB에 추가합니다',
            'params': {
                'name': '이름',
                'content': '내용',
                'description': '설명(선택사항)'
            },
            'example_json': '''{
  "name": "cafe_guide_prompt",
  "content": "당신은 카페 이용을 도와주는 가이드입니다. 다음 정보를 바탕으로 답변해주세요: {context}",
  "description": "카페 이용 정보를 제공하는 프롬프트"
}'''
        },
        {
            'name': '프롬프트_수정',
            'id': 'update-prompt',
            'url': '/chatbot/update-prompt/{id}/',
            'method': 'PUT',
            'description': 'Django DB의 프롬프트를 수정합니다. (프롬프트 ID 필요)',
            'params': {
                'name': '이름',
                'content': '내용',
                'description': '설명',
                'score': '점수',
                'num_exposure': '노출 횟수'
            },
            'example_json': '''{
  "name": "수정된 카페 가이드 프롬프트",
  "content": "당신은 친절한 카페 이용 안내자입니다. 다음 정보를 참고하여 답변해주세요: {context}",
  "description": "더 친절한 어조로 카페 이용 정보를 제공",
  "score": 10,
  "num_exposure": 25
}'''
        },
        {
            'name': '프롬프트_삭제',
            'id': 'delete-prompt',
            'url': '/chatbot/delete-prompt/{id}/',
            'method': 'DELETE',
            'description': 'Django DB의 프롬프트를 삭제합니다 (프롬프트 ID 필요)',
            'params': {},
            'example_json': ''
        }
    ]
    
    # 디버깅을 위한 출력
    for api in apis:
        print(f"API Name: {api['name']}, Slug ID: {api['id']}")
    
    return render(request, 'management/api_management.html', {'apis': apis})

@api_view(['POST'])
def hybrid_search(request):
    """하이브리드 검색 API 엔드포인트 (벡터 검색 + BM25 키워드 검색)"""
    data = request.data
    query = data.get('query', '')
    top_k = data.get('top_k', 5)
    filters = data.get('filters', None)
    vector_weight = data.get('vector_weight', 0.5)
    search_type = data.get('search_type', 'hybrid')  # 'hybrid', 'vector', 'bm25' 중 하나
    
    if not query:
        return Response({"error": "검색어를 입력해주세요."}, status=400)
    
    # 검색 유형 검증
    if search_type not in ['hybrid', 'vector', 'bm25']:
        return Response({"error": "검색 유형은 'hybrid', 'vector', 'bm25' 중 하나여야 합니다."}, status=400)
    
    # 벡터 가중치 검증 (0.0 ~ 1.0)
    try:
        vector_weight = float(vector_weight)
        if vector_weight < 0 or vector_weight > 1:
            return Response({"error": "벡터 가중치는 0.0과 1.0 사이의 값이어야 합니다."}, status=400)
    except (ValueError, TypeError):
        return Response({"error": "벡터 가중치는 숫자 형식이어야 합니다."}, status=400)
    
    # 검색 서비스 초기화
    advanced_retrieval = AdvancedRetrievalService()
    
    # 검색 유형에 따라 적절한 메서드 호출
    try:
        if search_type == 'hybrid':
            results = advanced_retrieval.hybrid_search(
                query_text=query,
                top_k=top_k,
                filter_dict=filters,
                vector_weight=vector_weight
            )
        elif search_type == 'vector':
            results = advanced_retrieval.pinecone_service.search_similar_documents(
                query_text=query,
                top_k=top_k,
                filter_dict=filters
            )
        else:  # 'bm25'
            results = advanced_retrieval.bm25_search(
                query_text=query,
                top_k=top_k,
                filter_dict=filters
            )
        
        return Response({
            "results": results,
            "search_type": search_type,
            "query": query,
            "vector_weight": vector_weight if search_type == 'hybrid' else None
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
def index_opensearch_data(request):
    """OpenSearch 데이터 인덱싱 API 엔드포인트"""
    try:
        advanced_retrieval = AdvancedRetrievalService()
        total_documents = advanced_retrieval.index_unindexed_data()
        
        return Response({
            "success": True,
            "total_documents": total_documents,
            "message": f"OpenSearch 인덱싱 완료. 총 {total_documents}개의 문서가 인덱싱되었습니다."
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
def clear_opensearch_index(request):
    """OpenSearch 인덱스 초기화 API 엔드포인트"""
    try:
        advanced_retrieval = AdvancedRetrievalService()
        result = advanced_retrieval.clear_opensearch_index()
        
        if result:
            message = "OpenSearch 인덱스가 성공적으로 초기화되었습니다."
            return Response({"success": True, "message": message})
        else:
            return Response({"error": "인덱스 초기화 중 오류가 발생했습니다."}, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
