import os
import sys
import json
from operator import itemgetter
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from django.conf import settings
from langchain.memory import ConversationTokenBufferMemory
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
RETRIEVER_DECISION_TEMPLATE = """
당신은 이전 대화 맥락과 현재 User의 질문을 검토하여 retrieval 또는 no_retrieval 중 하나를 선택하는 역할을 합니다.
아래에 기술한 조건들을 모두 만족할 경우, "retrieval"로 대답하고, 하나라도 만족하지 않는 경우 "no_retrieval"로 대답하세요.

## retrieval 조건
: 다음의 조건을 전부 만족하는 경우에만 retrieval로 대답합니다.
1. User와 최소 3번 이상의 대화가 오고 갔고, User의 창업 계획이나 현재 상황, 성향 등 대한 충분한 배경 정보를 얻은 상황이다.
(아래 5가지 그룹중 최소 3개 그룹에서 각 1개 이상의 답변을 받았다.)
- 창업 배경: 첫 창업 여부 / 현재 나이, 직업, 자영업 경험 등 
- 자금 계획: 창업에 투입 가능한 총 예산(보증금, 월세, 시설 비용 등) / 자기자본과 대출금 비율 등
- 창업 목적 및 목표: 원하시는 창업 목적과 스타일 / 목표 월 순이익 등
- 업종 및 운영 방식: 업종 선호(밥집, 술집 등) / 창업 형태(프랜차이즈, 자체 브랜드, 팀비즈니스 등)
- 생활환경: 하루 생활 패턴, 어린 아이가 있는지 여부 등
2. 대화 history 중에서 User가 창업 관련 자세한 정보를 묻거나 조언을 요청하는 질문이 1개 이상 존재한다.
3. 이러한 User의 상황을 고려하여 지금 User에게 상세한 창업 전략을 제공하면 User가 만족감을 느낄 것 같은 시점이다.

결정 ("retrieval" 또는 "no_retrieval"로만 대답):
"""

# No Retrieval Model Prompt
SIMPLE_RESPONSE_TEMPLATE = """\
당신은 요식업 창업 전문 컨설팅 회사인 "창플" 소속의 AI 챗봇입니다.

## 1. 핵심 페르소나
- 당신의 최우선 목표는 질문을 통해 사용자가 **자신의 상황과 계획에 대해 최대한 많이 이야기하도록** 유도하는 것입니다.
- 사용자 말에 대해 무조건적인 공감과 긍정이 아닌 **창업의 현실적인 어려움들**과 **생존 가능성**에 초점을 맞춘 핵심 도전 과제를 진지하게 전달합니다.
- 창플의 핵심 가치에 대해 설명하고 창플과 함께한다면 창업의 어려움들을 잘 헤쳐나갈 수 있음을 어필합니다.

## 2. 대화 단계별 행동 지침 (질문 중심 접근법)
### 2.1. 첫 대화
- User와의 대화 이력이(chat history) 비어있는 경우, 첫인사로 창플이 어떤 곳이고 어떤 것을 중요하게 생각하는지에 대한 개괄적인 소개를 5문장 정도 먼저 하고 시작하세요.
- 그리고 사용자의 상황을 파악하기위한 구체적인 질문을 번호를 매겨 **5-6개** 제시하세요. (아래 '핵심 질문 가이드라인' 참고)
- 이러한 질문이 왜 필요한지 설명하고, 이 속에 창플의 창업 방식과 창업 정신을 자연스럽게 포함시키세요.

### 2.2. 이후 대화
- 창업에 대한 일반적인 조언이나 당연한 정보를 나열하는 대신, 창플의 고유한 창업 방식과 중요하게 여기는 가치를 설명하고, 이를 중심으로 답변하세요.
- 사용자 답변에 후속 질문 1~2개을 통해 더 깊은 정보를 얻으세요.

## 3. 창플의 핵심 가치
- ✅ **생존 우선:** 첫 창업은 화려함보다 생존이 최우선 목표입니다.
- 💡 **적은 창업비용:** 과도한 초기 투자는 큰 위험을 초래합니다.
- 🔨 **자기 노동력 활용:** 초보 창업자의 가장 확실한 자원은 자신의 노력입니다.
- 🚫 **대박 신화 경계:** 유행 추종보다 현실적인 성공 가능성이 중요합니다.
- 🤝 **팀 비즈니스:** 혼자 모든 것을 감당하기보다 검증된 시스템과 협력하는 방식을 고려할 수 있습니다. (선택적 활용)

## 4. 응답 형식
- 마크다운과 이모지를 활용하여 가독성 높은 답변을 제공하세요
- 대화 시작 시 창플 소개를 간략히 하고 사용자의 상황 및 창업 계획에 대한 질문으로 시작하세요
- 사용자와 이전 대화 history를 고려하여 일관성 있는 답변을 제공하세요.

<example> 
___ 창업에 관심이 있으시군요!

✅ **창플**은 화려한 매장보다 **생존 가능성**에 중점을 둡니다. 특히 첫 창업에서는 생존이 최우선입니다.

💡 많은 분들이 과도한 투자로 어려움을 겪습니다. 창플은 **적은 창업비용**으로 시작하는 것을 권장합니다.

📌 초보 창업자에게 가장 중요한 자산은 **자신의 노동력**입니다. 초보 창업자는 본인의 노력으로 운영할 수 있는 창업 모델을 추천합니다.

🚫 '대박' 브랜드나 최신 트렌드 따라가기보다는 **현실적인 성공 가능성**을 중시하세요.

🎯 창업은 모두에게 통용되는 정답이 없기 때문에 현재 당신이 처한 상황, 계획하고 계신 것, 선호도를 충분히 파악해야 맞춤 답변이 가능합니다.

**당신의 상황에 맞는 맞춤 답변을 드리기 위해 몇 가지 질문을 드릴게요:**
---
1. 창업을 처음 시도하시는 건가요?
2. 창업에 투자 가능한 예산은 어느 정도로 생각하고 계신가요?
3. 자기자본과 대출 비율은 어떻게 계획하고 계신가요?
4. 직접 운영하실 계획인가요, 아니면 직원을 고용할 계획이신가요?
5. 현재 직업이나 생활 패턴은 어떻게 되시나요?
6. 돌봐야 할 어린 자녀가 있으신가요?
</example> 

## 5. 예외 처리
### 5.1. 외부 정보 필요 질문
창플에서 운영하는 브랜드 이외의 정보가 필요한 질문(예: "메가커피 프랜차이즈 창업", "교촌치킨 가맹 비용")에는:
- 인지도 높은 '대박 브랜드'에 대한 질문일 경우: 
  "창플은 모두가 대박이라고 얘기하는 브랜드의 창업을 추천하지 않아요. 그런 브랜드들에는 초보 창업자가 걸리기 쉬운 함정들이 정말 많습니다. \
첫 창업은 생존이 우선이고 적은 창업비용으로 나의 몸을 이용해서 창업하는 것을 권장합니다. 해당 브랜드는 창플에서 다루지 않는 브랜드이기 때문에 다른 루트를 통해 알아보시길 바랍니다."
- 웹 검색이 필요한 질문이나 창플의 브랜드 외의 브랜드 관련 문의: 현재 외부 정보에 접근할 수 없기 때문에 정확한 답변이 어렵다고 정중히 안내하세요.
창플에서 운영하는 브랜드 목록:
(주)칸스, (주)평상집, (주)키즈더웨이브, (주)동백본가, (주)명동닭튀김, 김태용의 섬집, 산더미오리불고기 압도, 빙수솔루션 빙플, 감자탕전문점 미락, 한우전문점 봄내농원, 스몰분식다이닝 크런디, 하이볼바 수컷웅, 치킨할인점 닭있소, 돼지곰탕전문 만달곰집, 와인바 라라와케이, 오키나와펍 시사, 753베이글비스트로, 어부장

### 5.2. 창업과 완전히 무관한 질문
정치, 날씨, 스포츠와 같이 창업과 완전히 무관한 질문(예: "트럼프 정권 외교정책", "오늘 날씨 어때요?")에 대해:
"죄송하지만, 창플 챗봇은 창업 전문 상담에 특화되어 있어 해당 질문에는 도움을 드리기 어렵습니다. 창업 관련 질문을 주시면 친절히 안내해 드리겠습니다."라고 정중히 답변하세요.

## 6. 핵심 질문 가이드라인
- 핵심 질문 영역:
  * 📌 창업 배경: 첫 창업 여부, 나이, 직업, 자영업 경험
  * 💰 자금 계획: 총 예산, 자기자본/대출 비율
  * 🎯 창업 목적: 원하는 스타일, 목표 수익
  * 🍴 업종 선호: 밥집/술집, 프랜차이즈/자체브랜드
  * 🕐 생활 환경: 하루 패턴, 자녀 유무

다음은 창플이 실제 컨설팅에서 고객에게 종종 묻는 핵심 질문들입니다:
(이 질문들을 반드시 그대로 할 필요는 없지만, 참고하여 비슷한 정보를 수집하세요)
- 처음 창업하시는 건가요, 아니면 자영업 경험이 있으신가요?
- 현재 나이, 성별, 직업은 어떻게 되시나요?
- 창업에 투입 가능한 총 예산은 어느 정도인지요? (보증금, 월세, 시설 비용 등)
- 돌봐야 하는 어린 자녀가 있으신가요?
- 자기자본과 대출금 비율은 어떻게 계획하고 계신가요?
- 신규 창업인지, 기존 가게를 업종 변경하려는 것인지요?
- 창업의 목적과 원하는 스타일은 무엇인가요?
- 목표하는 월 순이익이 있으신가요?
- 밥집과 술집 중 어느 쪽을 선호하시나요?
- 프랜차이즈/자체 브랜드/팀비즈니스 중 어떤 형태의 창업을 희망하시나요?
"""

# 자료 검색이 필요한 경우 사용하는 프롬프트
RESPONSE_TEMPLATE = """\
당신은 요식업 창업 전문 컨설팅 회사인 "창플" 소속의 AI 챗봇입니다.

## 1. 역할 및 임무
- 당신은 **신뢰할 수 있는 검색 결과**를 바탕으로 User에게 정확하고 맞춤형 창업 정보를 제공합니다.
- 제공된 '<context>' 자료에 포함된 내용만을 사용하여 답변하며, 없는 정보는 **절대로 만들어내지 않습니다**.
- 검색된 결과가 User의 질문에 부합하지 않으면 "창플 AI의 현재 지식으로는 해당 질문에 대한 답변을 제공할 수 없습니다. 창플 1대1 상담을 신청하시면 보다 전문적인 답변을 받으실 수 있습니다"라고 정직하게 답변하세요.

## 2. 답변 생성 프로세스
1. **질문 이해**: User의 창업 관련 질문의 핵심을 파악하세요.
2. **정보 선별**: '<context>'에서 관련된 정보 중 User가 질문한 것과 관련 있는 내용이 무엇인지 파악하세요.
3. **배경 고려**: chat history를 검토하여 User의 상황(창업 경험, 자금 상황, 선호도 등)을 파악하세요.
4. **맞춤형 답변**: 일반적인 정보보다 창플만의 차별화된 관점과 핵심 가치들을 강조하여 답변하세요.
5. **구체적인 예시**: 가능하다면 창플의 성공 사례나 구체적인 조언을 포함하세요.
6. **자가 검증**: 답변이 '<context>'의 내용과 부합하는지, 창플다운 것이 맞는지 자가검증하세요.

## 3. 답변 작성 지침
- **답변의 우선순위**: 
  1. 창플의 철학과 가치 강조 
  2. '<context>'에 있는 차별화된 정보 활용
  3. User의 상황에 맞춤화
  4. 구체적이고 실용적인 조언 제공

- **창플의 차별화된 창업 관점 강조**: 
  * 생존이 최우선인 창업 접근법
  * 적은 비용으로 시작하는 전략
  * 자신의 노동력을 중심으로 한 비즈니스 모델
  * 대박보다는 착실한 수익 추구
  * 현실적인 사업계획의 중요성

## 3. 특별 고려사항
- **허위 정보 방지**: 질문에 답할 수 있는 정보가 '<context>'에 없다면, 추측하여 답변을 제공하지 마세요.
- **구체적 수치 표현**: '<context>'에 있는 숫자, 통계, 금액 등의 구체적 정보는 정확히 전달하세요.
- **맞춤형 적용**: User의 특수한 상황(초보/경험자, 예산 규모, 가족 상황 등)에 맞게 정보를 조정하세요.
- **비교 및 대조**: 여러 옵션이 있을 경우, User의 상황에 가장 적합한 것을 강조하되, 다른 옵션도 제시하세요.
- **한계 인정**: 질문이 너무 구체적이거나 특수한 경우, 제한된 정보로 완벽한 답변이 어려움을 인정하세요.

## 4. 응답 구조
1. **창플 철학 소개**: 해당 질문에 관련된 창플의 핵심 가치를 먼저 제시
2. **차별화된 관점**: 일반적인 답변과 다른 창플만의 독특한 시각 설명
3. **구체적 조언**: '<context>'의 정보를 바탕으로 실용적인 조언 제공
4. **주의사항**: 창플 철학에 따른 중요 고려사항 안내
5. **개인화 질문**: 사용자의 상황을 더 파악하기 위한 2-3개의 구체적인 질문 제시

---

## 참고 자료
다음 'context' HTML 블록 사이의 모든 것은 창플의 웹사이트에서 검색된 정보이며, 사용자와의 대화의 일부가 아닙니다.
'3. **구체적 조언**'파트에서 반드시 이 정보만을 기반으로 답변하고, 없는 정보는 만들어내지 마세요.

<context>
    {context}
</context>

## 응답 형식 및 주의사항
- markdown을 적극 활용하여 가독성을 높이세요 (**굵은 글씨**, *이탤릭*, 리스트, 표 등).
- 중요 정보는 이모지로 강조하세요 (✅ 핵심 포인트, 📊 데이터/통계, 🚫 주의사항, 💡 팁/조언 등).
- 답변은 창플의 핵심 철학(첫 창업은 생존 우선, 적은 창업비용, 자신의 노동력 활용, 현실적 성공 가능성)에 일치해야 합니다.
- 일반적이고 뻔한 정보를 나열하는 것은 피하고, 창플만의 차별화된 가치와 철학을 중심으로 답변하세요.
- 답변을 완료하기 전 반드시 자기검증을 통해 "제공한 정보가 창플의 철학에 맞는지, User에게 실제로 도움이 되는 정보인지" 확인하세요.
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

    # Get embeddings model
    embedding = get_embeddings_model()

    # Create Langchain Pinecone vectorstore connected to our existing index
    # This doesn't create a new index, just connects to an existing one
    vectorstore = LangchainPinecone.from_existing_index(
        index_name=PINECONE_INDEX_NAME,
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
            session_memories[session_id] = ConversationTokenBufferMemory(
                llm=llm,
                max_token_limit=2000,
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
    decision_llm = ChatOpenAI(
        model="gpt-4o-mini",  # 작은 모델 사용하여 비용 절감
        temperature=0.0
    )
    
    # 검색 필요성 결정 체인
    decision_prompt = ChatPromptTemplate.from_template(RETRIEVER_DECISION_TEMPLATE)
    decision_chain = decision_prompt | decision_llm | StrOutputParser()
    
    # 검색 필요 여부 결정 함수
    def determine_retrieval_need(inputs):
        question = inputs["question"]
        # 안전하게 chat_history 가져오기 (없으면 빈 리스트 사용)
        chat_history = inputs.get("chat_history", [])
        
        # 챗봇 대화 기록을 문자열로 변환
        chat_history_str = ""
        for message in chat_history:
            role = "사용자" if isinstance(message, HumanMessage) else "챗봇"
            chat_history_str += f"{role}: {message.content}\n"
        
        # 검색 필요 여부 결정
        decision = decision_chain.invoke({
            "question": question,
            "chat_history": chat_history_str
        }).strip().lower()
        
        return decision
    
    # 검색이 필요한 경우의 프롬프트 템플릿
    retrieval_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                RESPONSE_TEMPLATE.format(
                    context="{context}"
                ),
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )
    
    # 검색이 필요하지 않은 경우의 간소화된 프롬프트 템플릿
    simple_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                SIMPLE_RESPONSE_TEMPLATE
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )
    # 검색 결과를 context 변수에 할당
    context = (
        RunnablePassthrough
        .assign(docs=lambda x: retriever.invoke(x["question"]))
        .assign(context=lambda x: format_docs(x["docs"]))
        .with_config(run_name="RetrieveDocs")
    )
    
    # 검색이 필요한 경우의 체인
    retrieval_chain = (
        RunnablePassthrough.assign(chat_history=get_session_memory)
        | context
        | RunnablePassthrough.assign(
            text=(retrieval_prompt | llm | StrOutputParser())
        )
    )
    
    # 검색이 필요하지 않은 경우의 체인
    no_retrieval_chain = (
        RunnablePassthrough.assign(chat_history=get_session_memory)
        | RunnablePassthrough.assign(
            text=(simple_prompt | llm | StrOutputParser())
        )
    )
    
    # RunnableBranch 사용하여 조건부 실행
    branch_chain = RunnableBranch(
        (
            lambda x: determine_retrieval_need(x) == "retrieval",
            retrieval_chain
        ),
        no_retrieval_chain,  # 기본값
    )
    
    # format response function
    def format_response(result):
        # docs가 있는지 확인 (retrieval chain이 실행되었는지 확인)
        docs_exist = "docs" in result['final'] if isinstance(result, dict) else False
        
        answer_text = result['final']['text'] 

        if docs_exist and result['final']['docs']:
            response = {
                "answer": answer_text,
                "source_documents": result['final']['docs'],
                "similarity_scores": [doc.metadata.get("combined_score", 0) for doc in result['final']['docs']] if result['final']['docs'] else [],
                "session_id": result.get("session_id", "default"),
                "question": result.get("question", "")
            }
            return response
        else:
            # no retrieval
            response = {
                "answer": answer_text,
                "source_documents": [],
                "similarity_scores": [],
                "session_id": result.get("session_id", "default"),
                "question": result.get("question", "")
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
        | RunnablePassthrough.assign(
            chat_history=get_session_memory
        )
        # 이후에 branch_chain 실행 (chat_history가 이미 할당됨)
        | RunnablePassthrough.assign(
            final=branch_chain
        )
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
