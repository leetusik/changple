from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from chatbot.services.pinecone_service import PineconeService
from chatbot.services.langchain_service import LangchainService
from chatbot.models import Prompt, ABTest
from django.conf import settings

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
    data = request.data
    start_post_id = data.get('start_post_id')
    num_document = data.get('num_document')
    
    pinecone_service = PineconeService()
    total_chunks = pinecone_service.process_cafe_data(
        start_post_id=start_post_id,
        num_document=num_document
    )
    
    return Response({"total_chunks": total_chunks})

@api_view(['GET'])
def get_pinecone_stats(request):
    """Pinecone 통계 정보 조회 API 엔드포인트"""
    pinecone_service = PineconeService()
    stats = pinecone_service.get_stats()
    
    return Response(stats)

@api_view(['POST'])
def chat(request):
    """챗봇 대화 API 엔드포인트"""
    data = request.data
    query = data.get('query', '')
    history = data.get('history', [])
    
    if not query:
        return Response({"error": "질문을 입력해주세요."}, status=400)
    
    langchain_service = LangchainService()
    response = langchain_service.generate_response(query, history)
    
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

@api_view(['POST'])
def run_ab_test(request):
    query = request.data.get('query')
    prompt_a_id = request.data.get('prompt_a')
    prompt_b_id = request.data.get('prompt_b')
    llm_model = request.data.get('llm_model', 'gpt-4o-mini')
    
    try:
        prompt_a = Prompt.objects.get(id=prompt_a_id)
        prompt_b = Prompt.objects.get(id=prompt_b_id)
        
        # Langchain 서비스 인스턴스 생성
        langchain_service = LangchainService()
        
        # 각 프롬프트로 응답 생성
        response_a = langchain_service.generate_response_custom_prompt(query, custom_prompt=prompt_a.content, model=llm_model)
        response_b = langchain_service.generate_response_custom_prompt(query, custom_prompt=prompt_b.content, model=llm_model)
        
        # settings에서 값 가져오기
        llm_temperature = getattr(settings, "LLM_TEMPERATURE", 0.7)
        llm_top_k = getattr(settings, "LLM_TOP_K", 5)
        chunk_size = getattr(settings, "TEXT_SPLITTER_CHUNK_SIZE", 1000)
        chunk_overlap = getattr(settings, "TEXT_SPLITTER_CHUNK_OVERLAP", 200)
        
        # 테스트 결과 저장
        test = ABTest.objects.create(
            query=query,
            prompt_a=prompt_a,
            prompt_b=prompt_b,
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

def ab_test_view(request):
    """A/B 테스트 페이지를 렌더링합니다."""
    prompts = Prompt.objects.all().order_by('-created_at')
    return render(request, 'chat/ab_test.html', {'prompts': prompts})

@api_view(['POST'])
def create_prompt(request):
    """프롬프트 생성 API 엔드포인트"""
    data = request.data
    
    try:
        prompt = Prompt.objects.create(
            prompt_id=data.get('prompt_id'),
            name=data.get('name'),
            content=data.get('content'),
            description=data.get('description', '')
        )
        
        return Response({
            "success": True,
            "prompt_id": prompt.id
        })
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['PUT'])
def update_prompt(request, prompt_id):
    """프롬프트 수정 API 엔드포인트"""
    data = request.data
    
    try:
        # 먼저 ID로 찾기
        try:
            prompt = Prompt.objects.get(id=prompt_id)
        except Prompt.DoesNotExist:
            # ID로 못 찾으면 prompt_id로 찾기 시도
            prompt = Prompt.objects.get(prompt_id=prompt_id)
        
        # 데이터 업데이트
        if 'prompt_id' in data:
            prompt.prompt_id = data['prompt_id']
        if 'name' in data:
            prompt.name = data['name']
        if 'content' in data:
            prompt.content = data['content']
        if 'description' in data:
            prompt.description = data['description']
        
        # 점수와 노출 수 필드도 업데이트 가능하도록 추가
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
        # 먼저 ID로 찾기
        try:
            prompt = Prompt.objects.get(id=prompt_id)
        except (Prompt.DoesNotExist, ValueError):
            # ID로 못 찾으면 prompt_id로 찾기 시도
            prompt = Prompt.objects.get(prompt_id=prompt_id)
        
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
