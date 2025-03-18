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
        
        # 임베딩 모델 초기화 (필요시에만)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=self.api_key
        )
        
        # 이미 있는 벡터스토어 가져오기
        self.vectorstore = self.pinecone_service.vectorstore
    
    def generate_response(self, query, history=None, k=3):
        """
        쿼리와 이전 대화 이력을 바탕으로 응답을 생성합니다.
        
        Args:
            query: 사용자 질문
            history: 대화 이력 (기본값: None)
            k: 검색할 문서 수
        """
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
        history_query = ""
        history_response = ""
        
        if history:
            # 대화 이력을 순회하면서 마지막 사용자와 AI 메시지 추출
            for msg in history:
                role = msg.get('role', '')
                content = msg.get('content', '')
                if role == 'user':
                    formatted_history += f"사용자: {content}\n"
                    history_query = content  # 마지막 사용자 메시지 저장
                elif role == 'assistant':
                    formatted_history += f"AI: {content}\n"
                    history_response = content  # 마지막 AI 메시지 저장
        
        # system 메시지와 human 메시지를 명시적으로 구분
        messages = [
            SystemMessagePromptTemplate.from_template(
                "당신은 창플의 대표입니다. 아래 글은 창플 대표가 쓴 글들입니다. 창플 철학을 학습하여, 이전 대화 맥락을 고려해 상담 고객의 질문에 답변해주세요:\n{context}"
            ),
        ]
        
        # 이전 대화 이력 메시지들 추가
        if formatted_history:
            messages.append(HumanMessagePromptTemplate.from_template("{history_query}"))
            messages.append(AIMessagePromptTemplate.from_template("{history_response}"))
        
        # 현재 질문 추가
        messages.append(HumanMessagePromptTemplate.from_template("{query}"))
        
        prompt = ChatPromptTemplate.from_messages(messages)
        
        # LangChain 모델 및 프롬프트 설정
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, openai_api_key=self.api_key)
        
        # LangChain 체인 생성 및 실행
        chain = LLMChain(llm=llm, prompt=prompt)
        
        # history_query와 history_response를 명시적으로 전달
        response = chain.run(
            context=combined_context, 
            history=formatted_history, 
            query=query,
            history_query=history_query,
            history_response=history_response
        )
        
        return response 