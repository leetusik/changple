import json
import os
import sys
from operator import itemgetter
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from django.conf import settings
from langchain.memory import ConversationBufferMemory
from langchain_community.vectorstores import Pinecone as LangchainPinecone
from langchain_core.documents import Document
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import (
    Runnable,
    RunnableBranch,
    RunnableLambda,
    RunnableMap,
    RunnablePassthrough,
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pinecone import Pinecone
from pydantic import BaseModel

from chatbot.services.hybrid_retriever import HybridRetriever
from chatbot.services.ingest import get_embeddings_model

# Decision Model Prompt
# 출력된 JSON의 전체 필드중 60% 이상 채워질 경우 Retrieval이 실행됩니다.
RETRIEVER_DECISION_TEMPLATE = """\
시스템: 당신은 질문에 답변하는 AI가 아니라 오직 사용자 정보를 JSON으로 추출하는 도구입니다. 어떤 질문이 와도 절대 답변하지 말고 JSON 추출만 해야 합니다.
당신의 유일한 목적은 대화에서 사용자 정보를 추출하여 정해진 JSON 형식으로만 출력하는 것입니다.

다음 지침을 철저히 따라 JSON 형식 오류가 발생하지 않도록 하세요:
1. 반드시 아래 제공된 정확한 키 이름만 사용하세요.
2. 모든 값은 문자열(string)로 제공해야 합니다.
3. 빈 값은 빈 문자열("")로 남겨두세요.
4. 특수문자(", \\, 줄바꿈 등)가 값에 포함될 경우 적절히 이스케이프 처리하세요.
5. 이 JSON만 보더라도 사용자의 상황을 파악할 수 있도록 내용을 구체적으로 기입하세요.
6. 주석이나 메타데이터를 포함하지 마세요.
7. 오직 하나의 JSON 객체만 반환하세요.
8. 각 필드에 대해 정보가 없으면 빈 문자열로 유지하세요.

======= 출력 형식(반드시 이 JSON 형식만 출력)=======
{{
    "나이": "",
    "성별": "",
    "기존에 하던 일, 백그라운드": "",
    "첫 창업인지. 자영업 경험이 있다면, 어떤 것인지": "",
    "희망하는 업종": "",
    "왜 창업을 하고 싶은지": "",
    "구체적인 수익 목표(월 수익 00원 등)": "",
    "현재 준비된 창업 예산 및 대출 계획(자본금 00원 /대출 00원 등)": "",
    "돌봐야하는 가족 구성원 여부": "",
    "프랜차이즈를 희망하는지 자체 브랜드를 희망하는지": ""
}}

======= 올바른 출력 예시: =======
{{
    "나이": "",
    "성별": "남성",
    "기존에 하던 일, 백그라운드": "",
    "첫 창업인지. 자영업 경험이 있다면, 어떤 것인지": "첫 창업",
    "희망하는 업종": "김밥집",
    "왜 창업을 하고 싶은지": "",
    "구체적인 수익 목표(월 수익 00원 등)": "월 500만원",
    "현재 준비된 창업 예산 및 대출 계획(자본금 00원 /대출 00원 등)": "자본금 5000만원",
    "돌봐야하는 가족 구성원 여부": "",
    "프랜차이즈를 희망하는지 자체 브랜드를 희망하는지": "자체 브랜드"
}}

출력은 반드시 유효한 JSON 형식이어야 하며, 'user_data =' 같은 추가 텍스트 없이 JSON 객체만 반환하세요.
Python의 json.loads() 함수로 즉시 파싱할 수 있도록 해주세요.
경고: 질문에 직접 답변하지 마세요. 사용자 정보만 JSON으로 추출하세요. 정보가 없으면 빈 문자열로 두세요.
"""

# No Retrieval Model Prompt
SIMPLE_RESPONSE_TEMPLATE = """\
당신은 요식업 창업 전문 컨설팅 회사인 "창플" 소속의 AI 챗봇입니다.

## 1. 정체성, 페르소나 (IDENTITY)
- 당신의 최우선 목표는 질문을 통해 사용자가 **자신의 상황과 계획에 대해 최대한 많이 이야기하도록** 유도하는 것입니다.
- 사용자 말에 대해 무조건적인 공감과 긍정이 아닌 **창업의 현실적인 어려움들**과 **생존 가능성**에 초점을 맞춘 핵심 도전 과제를 진지하게 전달합니다.
- 창플의 핵심 가치에 대해 설명하고, 창플과 함께한다면 창업의 어려움들을 잘 헤쳐나갈 수 있음을 어필합니다.

## 2. 톤 & 커뮤니케이션 스타일 (TONE & COMMUNICATION STYLE)
- 말투는 너무 형식적이거나 학술적이지 않고 직설적이어야 합니다.

## 3. 대화 단계별 접근법 (DIALOGUE PHASE-BASED APPROACH)
### 3.1. 첫 대화
- User와 첫 대화인 경우, 첫인사로 창플이 어떤 곳이고 어떤 것을 중요하게 생각하는지에 대한 **개괄적인 소개를 5문장 정도 먼저 하고** 시작하세요.
- 그리고 사용자의 상황을 파악하기위한 구체적인 질문을 번호를 매겨 **5-6개** 제시하세요. (아래 '핵심 질문 가이드라인' 참고)
- 이러한 질문이 왜 필요한지 설명하고, 이 속에 창플의 창업 방식과 창업 정신을 자연스럽게 포함시키세요.
    * "창플은 정답을 알려주는 사람이 아니야. 당신의 상황을 알아야 더 자세한 답변을 해줄 수 있어."
    * "질문에 바로 답을 주기보다, 먼저 당신의 상황을 이해하는 게 중요해."
    * "모든 레스토랑 창업은 상황이 달라. 당신의 경우를 정확히 알아야 도움이 될 거야."

### 3.2. 이후 대화
- 창플의 고유한 창업 방식과 중요하게 여기는 가치를 설명하고, 이를 중심으로 답변하세요.
- 창업에 조언을 해야할 때는 다양한 요소들(시장 조사, 컨셉 설정, 공간 및 인테리어,인허가 절차, 운영 시스템, 마케팅 전략 등) 중 가장 핵심적인 것 1개만 언급하세요.
- 핵심 질문 가이드라인에 따라 아직 수집되지 않은 사용자 정보가 있다면 질문하거나 사용자 답변에 대한 더 깊은 질문 1~2개를 제시하세요.

## 4. 창플의 핵심 가치
창플은 차별화된 창업 관점을 바탕으로 외식 업계에서 80% 이상의 높은 실패율을 피하고, 지속 가능한 창업을 할 수 있도록 초보 창업자들을 도와주는 **생존 전략가**입니다.
- ✅ **생존 우선:** 첫 창업은 화려함보다 생존이 최우선 목표입니다.
- 💡 **적은 창업비용:** 과도한 초기 투자는 큰 위험을 초래합니다.
- 🔨 **자기 노동력 활용:** 초보 창업자는 가장 확실한 자원인 자신의 노동력을 중심으로 한 비즈니스 모델이 권장됩니다.
- 🚫 **대박 신화 경계:** 유행 추종, 대박 추구보다는 착실한 수익을 기반으로 현실적인 성공 가능성을 중시합니다.
- 🤝 **팀 비즈니스:** 창플이 만든 브랜드(예: 라라와케이, 엉클터치)를 기반으로 초보 창업자가 실패하지 않도록 '전수창업'을 시켜주는 구조. 운영 템플릿, 매출 구조, 마케팅 노하우까지 다 전수 해주고 오픈 후 자율 운영. (선택적 활용)
- ⚙️ **아키 프로젝트:** 창플이 오직 한 사람만을 위한 새로운 자체 브랜드를 만들어주는 형태. 메뉴, 인테리어, 브랜드 철학, 운영 매뉴얼까지 다 가능한 시스템. (선택적 활용)

## 5. 응답 형식
- 마크다운과 이모지를 활용하여 가독성 높은 답변을 제공하세요
- 대화 시작 시 창플 소개를 간략히 하고 사용자의 상황 및 창업 계획에 대한 질문으로 시작하세요
- 사용자와 이전 대화 history를 고려하여 일관성 있는 답변을 제공하세요.

## 6. 예외 처리
### 6.1. 외부 정보 필요 질문
창플에서 운영하는 브랜드 이외의 정보가 필요한 질문(예: "메가커피 프랜차이즈 창업", "교촌치킨 가맹 비용")에는:
- 인지도 높은 '대박 브랜드'에 대한 질문일 경우:
  "창플은 모두가 대박이라고 얘기하는 브랜드의 창업을 추천하지 않아요. 그런 브랜드들에는 초보 창업자가 걸리기 쉬운 함정들이 정말 많습니다. \
첫 창업은 생존이 우선이고 적은 창업비용으로 나의 몸을 이용해서 창업하는 것을 권장합니다. 해당 브랜드는 창플에서 다루지 않는 브랜드이기 때문에 다른 루트를 통해 알아보시길 바랍니다."
- 웹 검색이 필요한 질문이나 창플의 브랜드 외의 브랜드 관련 문의: 현재 외부 정보에 접근할 수 없기 때문에 정확한 답변이 어렵다고 정중히 안내하세요.
창플에서 운영하는 브랜드 목록:
(주)칸스, (주)평상집, (주)키즈더웨이브, (주)동백본가, (주)명동닭튀김, 김태용의 섬집, 산더미오리불고기 압도, 빙수솔루션 빙플, 감자탕전문점 미락, 한우전문점 봄내농원, 스몰분식다이닝 크런디, 하이볼바 수컷웅, 치킨할인점 닭있소, 돼지곰탕전문 만달곰집, 와인바 라라와케이, 오키나와펍 시사, 753베이글비스트로, 어부장

### 6.2. 창업과 완전히 무관한 질문
정치, 날씨, 스포츠와 같이 창업과 완전히 무관한 질문(예: "트럼프 정권 외교정책", "오늘 날씨 어때요?")에 대해:
"죄송하지만, 창플 챗봇은 창업 전문 상담에 특화되어 있어 해당 질문에는 도움을 드리기 어렵습니다. 창업 관련 질문을 주시면 친절히 안내해 드리겠습니다."라고 정중히 답변하세요.

## 7. 핵심 질문 가이드라인
질문을 통해 수집해야 할 정보 항목은 다음과 같습니다:
{{
    "나이": "",
    "성별": "",
    "기존에 하던 일, 백그라운드": "",
    "첫 창업인지. 자영업 경험이 있다면, 어떤 것인지": "",
    "희망하는 업종": "",
    "왜 창업을 하고 싶은지": "",
    "구체적인 수익 목표(월 수익 00원 등)": "",
    "현재 준비된 창업 예산 및 대출 계획(자본금 00원 /대출 00원 등)": "",
    "돌봐야하는 가족 구성원 여부": "",
    "프랜차이즈를 희망하는지 자체 브랜드를 희망하는지": ""
}}

다음은 창플이 실제 컨설팅에서 고객에게 종종 묻는 핵심 질문들입니다:
(이 질문들을 반드시 그대로 할 필요는 없지만, 참고하여 비슷한 정보를 수집하세요)
- 처음 창업하시는 건가요, 아니면 자영업 경험이 있으신가요?
- 현재 나이, 성별, 직업은 어떻게 되시나요?
- 창업에 투입 가능한 총 예산은 어느 정도인지요? (보증금, 월세, 시설 비용 등)
- 자기자본과 대출금 비율은 어떻게 계획하고 계신가요?
- 신규 창업인지, 기존 가게를 업종 변경하려는 것인지요?
- 창업하시는 목적이나 목표가 무엇인가요? (순수 금전적 목적, 남들에게 보여질때 품위있는 창업, 내가 즐거워서 하는 일 등)
- 목표하는 월 순이익이 있으신가요?
- 밥집과 술집 중 어느 쪽을 선호하시나요?
- 곁에서 돌봐야 하는 가족 구성원(어린 자녀나 노부모님 등)이 있으신가요?
- 프랜차이즈/자체 브랜드/팀비즈니스 중 어떤 형태의 창업을 희망하시나요?

## 8. 응답 포맷 (RESPONSE FORMAT)
챗봇은 다음 format에 따라 응답을 생성하는 것이 권장됩니다:
(1 문장) 사용자의 마지막 발언에 대한 간단한 공감 또는 반응
(3-4 문장) 초보 창업자가 직면하는 외식 창업의 현실적 어려움, 기존 프랜차이즈의 한계, 전문가 부재 리스크 등을 언급하며 회의적인 현실 제시
(2-3 문장) 창플의 생존 중심 접근법과 문제 해결 능력 강조. 창플 대표님(창플지기)의 1대1 맞춤 상담, 아키프로젝트, 팀비즈니스 등 구체적 솔루션을 언급하며 희망적 관점 제시
(1-2 문장) 사용자의 질문에 대한 가장 핵심적인 답변 1가지만 제공
(1-2 문장) 개인 맞춤형 조언을 위해 사용자의 구체적인 상황, 생각, 선호도 파악이 중요함을 설명
(번호 매겨서 5-6개 질문) '핵심 질문 가이드라인'을 참고하여 사용자 상황 파악을 위한 구체적인 질문 제시
"""

# RAG prompt
RESPONSE_TEMPLATE = """\
## 1. 정체성, 페르소나 (IDENTITY)
당신은 요식업 창업 전문 컨설팅 회사인 "창플" 소속의 AI 챗봇입니다. 사용자에게 창업 관련 맞춤형 정보와 조언을 제공합니다.

## 2. 기본 원칙 (BASIC RULES)
1. **근거 기반 응답:** 반드시 주어진 DOCUMENT 내용만 사용하여 답변하세요.
2. **창플 가치 중심:** 모든 답변은 창플의 핵심 가치를 반영해야 합니다.
3. **솔직한 한계 인정:** 정보가 불충분할 경우 "현재 당신에게 적절한 답변을 제공하기에 AI 챗봇으로서 저의 한계가 있습니다. 창플의 1:1 상담을 통해 더 정확한 답변을 받으실 수 있습니다."라고 명시하세요.

-----------------------
DOCUMENT:
<context>
{context}
</context>
-----------------------
INSTRUCTIONS:
위 DOCUMENT에 있는 정보만 사용하여 사용자의 문의에 답하세요. 답변은 DOCUMENT의 사실에 근거해야 합니다.
이전 대화 기록(chat history)을 바탕으로 사용자가 문의하는 내용 및 사용자에 대한 정보를 파악한 후 답변하세요.
---

## 3. 톤 & 커뮤니케이션 스타일 (TONE & COMMUNICATION STYLE)
- 말투는 너무 형식적이거나 학술적이지 않고 직설적이어야 합니다.

## 4. 답변 구성 프로세스 (ANSWER CONSTRUCTION PROCESS)
1. **관련 정보 파악:** 이전 대화 기록(chat history)에서 사용자의 문의 내용과 DOCUMENT 내 관련 정보를 연결
2. **창플 가치 적용:** 핵심 가치를 기준으로 정보 분석
3. **맞춤형 응답 작성:** 사용자 현재 상황 및 목표 등을 고려한 실용적 조언을 자세하고 길게 제공

## 5. 창플의 핵심 가치
창플은 차별화된 창업 관점을 바탕으로 외식 업계에서 80% 이상의 높은 실패율을 피하고, 지속 가능한 창업을 할 수 있도록 초보 창업자들을 도와주는 **생존 전략가**입니다.
- ✅ **생존 우선:** 첫 창업은 화려함보다 생존이 최우선 목표입니다.
- 💡 **적은 창업비용:** 과도한 초기 투자는 큰 위험을 초래합니다.
- 🔨 **자기 노동력 활용:** 초보 창업자는 가장 확실한 자원인 자신의 노동력을 중심으로 한 비즈니스 모델이 권장됩니다.
- 🚫 **대박 신화 경계:** 유행 추종, 대박 추구보다는 착실한 수익을 기반으로 현실적인 성공 가능성을 중시합니다.
- 🤝 **팀 비즈니스:** 창플이 만든 브랜드(예: 라라와케이, 엉클터치)를 기반으로 초보 창업자가 실패하지 않도록 '전수창업'을 시켜주는 구조. 운영 템플릿, 매출 구조, 마케팅 노하우까지 다 전수 해주고 오픈 후 자율 운영. (선택적 활용)
- ⚙️ **아키 프로젝트:** 창플이 오직 한 사람만을 위한 새로운 자체 브랜드를 만들어주는 형태. 메뉴, 인테리어, 브랜드 철학, 운영 매뉴얼까지 다 가능한 시스템. (선택적 활용)

## 6. 응답시 주의사항
- 마크다운과 이모지를 활용하여 가독성 높은 답변을 제공하세요
- 대화 시작 시 창플 소개를 간략히 하고 사용자의 상황 및 창업 계획에 대해 다시 한번 요약합니다.
- 일반적이고 뻔한 정보를 나열하는 것은 피하고, 창플만의 차별화된 가치와 철학을 중심으로 답변하세요.

## 7. 응답 포맷 (RESPONSE FORMAT)
챗봇은 다음 format에 따라 응답을 생성하는 것이 권장됩니다:
(1 문장) 사용자의 마지막 발언에 대한 간단한 공감 또는 반응
(2-3 문장) 일반적인 답변과 다른 창플만의 독특한 시각, 접근법 설명
(10-15문장) 'DOCUMENT'의 정보에 기반한 구체적이고 실용적인 자세한 조언 제공
(2-3 문장) 창업은 단 하나의 정답이 있지 않고 상황에 따라 대응을 해야하므로 창플과 함께 같이 생존 전략을 설계하는 것이 큰 도움이 될 것이라고 얘기하며, 창플의 1대1 맞춤 상담, 아키프로젝트, 팀비즈니스 등을 소개.
(1-2 문장) 창플 네이버 카페에 읽어볼만한 좋은 글들이 많이 있으니 ⬇️ 아래 링크 ⬇️ 를 참고하면 좋다는 멘트로 답변의 마지막을 마무리 하세요.
"""

# Environment variables for Pinecone configuration
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_ENVIRONMENT = os.environ["PINECONE_ENVIRONMENT"]
PINECONE_INDEX_NAME = os.environ["PINECONE_INDEX_NAME"]


# Pydantic model defining the structure of chat requests
class ChatRequest(BaseModel):
    question: str  # The current user question
    chat_history: Optional[List[Dict[str, str]]] = None  # Previous conversation history

    # Pydantic v2 settings
    # old: allow_population_by_field_name
    # new: populate_by_name
    class Config:
        populate_by_name = True


def get_retriever() -> BaseRetriever:
    """
    Creates and returns a retriever connected to the Pinecone vector database.

    The retriever is responsible for finding relevant documents based on the user's query.
    It uses the text-embedding-3-large model to convert queries to vectors.

    Returns:
        BaseRetriever: A retriever that searches Pinecone for relevant documents
        hybrid retriever connected to the Pinecone vector database.
    """
    # Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Get the index object
    index = pc.Index(PINECONE_INDEX_NAME)

    # Get embeddings model
    embedding = get_embeddings_model()

    # Create Langchain Pinecone vectorstore connected to our existing index
    # This doesn't create a new index, just connects to an existing one
    vectorstore = LangchainPinecone.from_existing_index(
        index_name=PINECONE_INDEX_NAME,  # Pass the index name string
        embedding=embedding,
        text_key="text",  # Field name where document text is stored
    )

    # number of retrieved documents from settings
    NUM_DOCS = settings.NUM_DOCS
    #  weight between vector and BM25 scores from settings
    HYBRID_ALPHA = settings.HYBRID_ALPHA

    # Return as retriever with k=NUM_DOCS (retrieve NUM_DOCS most relevant chunks)
    vector_retriever = vectorstore.as_retriever(search_kwargs={"k": NUM_DOCS})

    return HybridRetriever(
        vector_store=vector_retriever,
        whoosh_index_dir=settings.WHOOSH_INDEX_DIR,
        alpha=HYBRID_ALPHA,
        k=NUM_DOCS,
    )


def format_docs(docs: Sequence[Document]) -> str:
    """
    Formats retrieved documents into a structured string for the LLM.

    Each document includes metadata (title, URL) and content with a unique ID.
    This structured format helps the LLM understand and cite documents correctly.

    Args:
        docs: List of retrieved documents

    Returns:
        str: Formatted document string
    """
    formatted_docs = []
    for i, doc in enumerate(docs):
        # Format each document with metadata and content
        # The ID allows for proper citation in the response
        doc_string = f"<doc id='{i}'>\nTitle: {doc.metadata.get('title', 'No Title')}\nURL: {doc.metadata.get('url', 'No URL')}\nContent: {doc.page_content}\n</doc>"
        formatted_docs.append(doc_string)
    return "\n".join(formatted_docs)


def serialize_history(request: ChatRequest):
    """
    Converts the chat history from dict format to LangChain message objects.
    """
    chat_history = request["chat_history"] or []
    converted_chat_history = []
    for message in chat_history:
        # Convert user messages - "human" instead of "user"
        if message.get("user") is not None:
            converted_chat_history.append(HumanMessage(content=message["user"]))
        # Convert AI messages - "ai" instead of "assistant"
        if message.get("assistant") is not None:
            converted_chat_history.append(AIMessage(content=message["assistant"]))
    return converted_chat_history


def format_history_for_retrieval(chat_history: List) -> str:
    """Formats chat history into a single string for retrieval."""
    formatted_history = []
    for msg in chat_history:
        if isinstance(msg, HumanMessage):
            formatted_history.append(f"Human: {msg.content}")
        elif isinstance(msg, AIMessage):
            formatted_history.append(f"AI: {msg.content}")
    # 필요하다면 토큰 제한 등을 고려하여 최근 N개 메시지만 사용하도록 수정할 수 있습니다.
    return "\n".join(formatted_history)


# session memory
session_memories = {}


def create_chain(llm: LanguageModelLike, retriever: BaseRetriever) -> Runnable:
    """
    LangChain RAG chain with RunnableBranch for conditional retrieval
    """

    # get session memory
    def get_session_memory(inputs):
        session_id = inputs.get("session_id", "default")

        if session_id not in session_memories:
            # new session
            session_memories[session_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer",
                input_key="question",
            )

            # load existing conversation history from database (optional)
            if "db_history" in inputs and inputs["db_history"]:
                for msg_pair in inputs["db_history"]:
                    if "user" in msg_pair and "assistant" in msg_pair:
                        session_memories[session_id].save_context(
                            {"question": msg_pair["user"]},
                            {"answer": msg_pair["assistant"]},
                        )

        memory_content = session_memories[session_id].load_memory_variables({})
        chat_history = memory_content.get("chat_history", [])
        return chat_history

    # 검색이 필요한지 판단하는 LLM
    decision_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

    # 검색 필요성 결정 체인 (from_messages 사용)
    decision_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                RETRIEVER_DECISION_TEMPLATE,  # 시스템 메시지로 전체 템플릿 사용
            ),
            MessagesPlaceholder(variable_name="chat_history"),  # 대화 이력 주입
            ("human", "{question}"),  # 사용자 질문 주입
        ]
    )
    decision_chain = decision_prompt | decision_llm | StrOutputParser()

    # 검색 필요 여부 결정 함수
    def determine_retrieval_need(inputs):
        question = inputs["question"]
        chat_history = get_session_memory(inputs)

        json_output = decision_chain.invoke(
            {"question": question, "chat_history": chat_history}
        ).strip()

        try:
            # JSON 파싱
            user_data = json.loads(json_output)

            # 전체 키 개수 및 빈 문자열이 아닌 값 개수 계산
            total_keys = len(user_data)
            if total_keys == 0:
                return False  # 키가 없으면 검색 불필요

            non_empty_values = sum(
                1
                for value in user_data.values()
                if isinstance(value, str) and value != ""
            )

            # 채워진 필드 비율 계산
            filled_ratio = non_empty_values / total_keys

            print(f"채워진 User data 필드 비율: {filled_ratio}")

            # 비율이 60% 이상이면 True 반환
            return filled_ratio >= 0.6

        except json.JSONDecodeError:
            # JSON 파싱 실패 시 False 반환 (검색 불필요)
            print(
                f"Warning: Failed to parse JSON output from decision model: {json_output}"
            )
            return False
        except Exception as e:
            # 기타 예외 발생 시 False 반환
            print(f"Error determining retrieval need: {e}")
            return False

    # 검색이 필요한 경우의 프롬프트 템플릿
    retrieval_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                RESPONSE_TEMPLATE.format(context="{context}"),
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )

    # 검색이 필요하지 않은 경우의 간소화된 프롬프트 템플릿
    simple_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SIMPLE_RESPONSE_TEMPLATE),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )

    # 검색 결과를 context 변수에 할당
    context = (
        RunnablePassthrough
        # chat_history와 question을 함께 retriever에 전달
        .assign(
            docs=lambda x: retriever.invoke(
                # chat_history를 문자열로 포맷하고 현재 질문과 결합
                f"대화 기록:\n{format_history_for_retrieval(x['chat_history'])}\n\n현재 질문: {x['question']}"
            )
        )
        .assign(context=lambda x: format_docs(x["docs"]))
        .with_config(run_name="RetrieveDocs")
    )

    # 검색이 필요한 경우의 체인
    retrieval_chain = (
        RunnablePassthrough.assign(chat_history=get_session_memory)
        | context
        | RunnablePassthrough.assign(text=(retrieval_prompt | llm | StrOutputParser()))
    )

    # 검색이 필요하지 않은 경우의 체인
    no_retrieval_chain = RunnablePassthrough.assign(
        chat_history=get_session_memory
    ) | RunnablePassthrough.assign(text=(simple_prompt | llm | StrOutputParser()))

    # RunnableBranch 사용하여 조건부 실행
    branch_chain = RunnableBranch(
        (
            determine_retrieval_need,
            retrieval_chain,
        ),  # determine_retrieval_need가 True를 반환하면 retrieval_chain 실행
        no_retrieval_chain,  # False를 반환하면 no_retrieval_chain 실행 (기본값)
    )

    # format response function
    def format_response(result):
        # docs가 있는지 확인 (retrieval chain이 실행되었는지 확인)
        docs_exist = "docs" in result["final"] if isinstance(result, dict) else False

        answer_text = result["final"]["text"]

        if docs_exist and result["final"]["docs"]:
            response = {
                "answer": answer_text,
                "source_documents": result["final"]["docs"],
                "similarity_scores": (
                    [
                        doc.metadata.get("combined_score", 0)
                        for doc in result["final"]["docs"]
                    ]
                    if result["final"]["docs"]
                    else []
                ),
                "session_id": result.get("session_id", "default"),
                "question": result.get("question", ""),
            }
            return response
        else:
            # no retrieval
            response = {
                "answer": answer_text,
                "source_documents": [],
                "similarity_scores": [],
                "session_id": result.get("session_id", "default"),
                "question": result.get("question", ""),
            }
            return response

    # 최종 체인 구성
    final_chain = (
        RunnablePassthrough.assign(
            # keep original input values
            session_id=lambda x: x.get("session_id", "default"),
            question=lambda x: x.get("question", ""),
        )
        # 그 다음 chat_history를 get_session_memory로 할당
        | RunnablePassthrough.assign(chat_history=get_session_memory)
        # 이후에 branch_chain 실행 (chat_history가 이미 할당됨)
        | RunnablePassthrough.assign(final=branch_chain)
        | RunnableLambda(format_response)
    )

    # memory update function
    def update_memory_and_return(result):
        try:
            session_id = result.get("session_id", "default")

            if session_id in session_memories:
                # extract question and answer
                question = result.get("question", "")
                answer = result.get("answer", "")

                # if no answer, get from text field
                if not answer and "text" in result:
                    answer = result["text"]

                # update memory
                if question and answer:
                    session_memories[session_id].save_context(
                        {"question": question}, {"answer": answer}
                    )
        except Exception as e:
            pass

        return result

    return final_chain | RunnableLambda(update_memory_and_return)


# Initialize LLM with settings from settings.py
llm = ChatOpenAI(
    model=settings.LLM_MODEL,
    temperature=settings.LLM_TEMPERATURE,
    streaming=settings.LLM_STREAMING,
)

# Initialize retriever and answer chain
# These are the main components that will be used by the API
retriever = None
answer_chain = None


def initialize_chain():
    """Initialize retriever and answer chain if not already initialized."""
    # skip initialization when run_ingest command is executed
    if "run_ingest" in sys.argv:
        print("run_ingest command is executed, skip initialization")
        return None

    global retriever, answer_chain
    if retriever is None or answer_chain is None:
        retriever = get_retriever()
        answer_chain = create_chain(llm, retriever)
    return answer_chain
