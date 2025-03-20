"""
Langchain service for the chatbot application.
This module contains functionality for langchain integration.
"""

# Import necessary libraries
import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Pinecone as LangchainPinecone
from pinecone import Pinecone
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate
from chatbot.services.openai_service import OpenAIService
from chatbot.services.pinecone_service import PineconeService
from django.conf import settings

class LangchainService:
    """
    Service for handling Langchain functionality.
    """
    def __init__(self):
        # OpenAI API 키 가져오기
        openai_service = OpenAIService()
        self.api_key = openai_service.api_key
        
        # Pinecone 서비스 초기화
        self.pinecone_service = PineconeService()
        
        # 임베딩 모델 초기화 (settings.py에서 모델명 가져오기)
        self.embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=self.api_key
        )
        
        # 이미 있는 벡터스토어 가져오기
        self.vectorstore = self.pinecone_service.vectorstore
    
    def generate_response(self, query, history=None, k=None):
        """
        쿼리와 이전 대화 이력을 바탕으로 응답을 생성합니다.
        
        Args:
            query: 사용자 질문
            history: 대화 이력 (기본값: None)
            k: 검색할 문서 수 (기본값: settings.py에서 설정된 값)
        """
        # k 값이 None이면 settings에서 가져오기
        if k is None:
            k = getattr(settings, 'LLM_TOP_K', 3)
            
        # 이력이 None이면 빈 리스트로 초기화
        if history is None:
            history = []
        
        # 관련 문서 검색
        search_results = self.pinecone_service.search_similar_documents(query, top_k=k)
        
        # 선택된 문서에서 텍스트와 메타데이터 추출
        context_texts = []
        for result in search_results:
            title = result['metadata'].get('title', '제목 없음')
            context_text = f"제목: {title}\n내용: {result['content']}\n"
            context_texts.append(context_text)
        
        # 모든 컨텍스트 텍스트 결합
        combined_context = "\n".join(context_texts)
        
        # 대화 이력 포맷팅
        formatted_history = ""
        
        if history:
            # 전체 대화 이력을 순회하며 포맷팅
            for msg in history:
                role = msg.get('role', '')
                content = msg.get('content', '')
                if role == 'user':
                    formatted_history += f"사용자: {content}\n"
                elif role == 'assistant':
                    formatted_history += f"AI: {content}\n"
        
        # system 메시지와 human 메시지를 명시적으로 구분
        messages = [
            SystemMessagePromptTemplate.from_template(
                "당신은 창플의 대표입니다. 아래 글은 창플 대표가 쓴 글들입니다. 창플 철학을 학습하여, 이전 대화 맥락을 고려해 상담 고객의 질문에 답변해주세요:\n{context}"
            ),
        ]
        
        # 이전 대화 이력이 있으면 하나의 컨텍스트로 추가
        if formatted_history:
            messages.append(SystemMessagePromptTemplate.from_template("\n이전 대화 내역:\n{history}")) # history 자리를 만들어주는 것
        
        # 현재 질문 추가
        messages.append(HumanMessagePromptTemplate.from_template("{query}"))
        
        prompt = ChatPromptTemplate.from_messages(messages)
        
        # LangChain 모델 및 프롬프트 설정
        llm = ChatOpenAI(
            model=getattr(settings, 'LLM_MODEL', 'gpt-4o-mini'), 
            temperature=getattr(settings, 'LLM_TEMPERATURE', 0.7), 
            openai_api_key=self.api_key
        )
        
        # LangChain 체인 생성 및 실행
        chain = LLMChain(llm=llm, prompt=prompt)
        
        # 체인 실행 - history_query, history_response 대신 전체 formatted_history 사용
        response = chain.run(
            context=combined_context, 
            history=formatted_history, # history 자리에 formatted_history 넣어주는 것
            query=query
        )
        
        return response 

    def generate_response_custom_prompt(self, query, custom_prompt=None, history=None, k=None, model=None):
        """
        커스텀 프롬프트를 사용하여 응답을 생성합니다.
        
        Args:
            query: 사용자 질문
            custom_prompt: 사용자 정의 프롬프트 템플릿
            history: 대화 이력 (기본값: None)
            k: 검색할 문서 수 (기본값: settings.py에서 설정된 값)
            model: 사용할 LLM 모델 (기본값: settings.py에서 설정된 값)
        """
        # k 값이 None이면 settings에서 가져오기
        if k is None:
            k = getattr(settings, 'LLM_TOP_K', 3)
        
        # 이력이 None이면 빈 리스트로 초기화
        if history is None:
            history = []
        
        # 모델이 None이면 settings에서 가져오기
        if model is None:
            model = getattr(settings, 'LLM_MODEL', 'gpt-4o-mini')
        
        # 관련 문서 검색
        search_results = self.pinecone_service.search_similar_documents(query, top_k=k)
        
        # 선택된 문서에서 텍스트와 메타데이터 추출
        context_texts = []
        for result in search_results:
            title = result['metadata'].get('title', '제목 없음')
            context_text = f"제목: {title}\n내용: {result['content']}\n"
            context_texts.append(context_text)
        
        # 모든 컨텍스트 텍스트 결합
        combined_context = "\n".join(context_texts)
        
        # 대화 이력 포맷팅
        formatted_history = ""
        
        if history:
            # 전체 대화 이력을 순회하며 포맷팅
            for msg in history:
                role = msg.get('role', '')
                content = msg.get('content', '')
                if role == 'user':
                    formatted_history += f"사용자: {content}\n"
                elif role == 'assistant':
                    formatted_history += f"AI: {content}\n"
        
        # 커스텀 프롬프트 사용 시 자리표시자 {context}와 {query} 사용
        if custom_prompt:
            system_template = custom_prompt
        else:
            system_template = "당신은 친절한 AI assistant입니다.\n{context}"
        
        # system 메시지와 human 메시지를 명시적으로 구분
        messages = [
            SystemMessagePromptTemplate.from_template(system_template),
        ]
        
        # 이전 대화 이력이 있으면 하나의 컨텍스트로 추가
        if formatted_history:
            messages.append(SystemMessagePromptTemplate.from_template("\n이전 대화 내역:\n{history}"))
        
        # 현재 질문 추가
        messages.append(HumanMessagePromptTemplate.from_template("{query}"))
        
        prompt = ChatPromptTemplate.from_messages(messages)
        
        # LangChain 모델 및 프롬프트 설정
        llm = ChatOpenAI(
            model=model, 
            temperature=getattr(settings, 'LLM_TEMPERATURE', 0.7), 
            openai_api_key=self.api_key
        )
        
        # LangChain 체인 생성 및 실행
        chain = LLMChain(llm=llm, prompt=prompt)
        
        # 체인 실행
        response = chain.run(
            context=combined_context, 
            history=formatted_history, 
            query=query
        )
        
        return response 