from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from chatbot.services.pinecone_service import PineconeService
from chatbot.services.langchain_service import LangchainService
from datetime import datetime

# Create your views here.

def index(request):
    # 템플릿 렌더링으로 변경
    return render(request, 'index.html')

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
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    limit = data.get('limit')
    
    # 날짜 형식 변환
    start_date = datetime.fromisoformat(start_date_str) if start_date_str else None
    end_date = datetime.fromisoformat(end_date_str) if end_date_str else None
    
    pinecone_service = PineconeService()
    processed_count = pinecone_service.process_cafe_data(
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    return Response({"processed_documents": processed_count})

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
    
    return Response({"response": response})
