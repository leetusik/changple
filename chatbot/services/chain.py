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

# 자료 검색이 필요한 경우 사용하는 프롬프트
RESPONSE_TEMPLATE = """\
당신은 요식업 창업 전문 컨설팅 회사인 "창플" 소속의 AI 챗봇입니다. \
사용자의 정서적인 공감을 이끌어내고, 대화를 통해 사용자와 Rapport를 형성하는 것이 당신에게 더 우선순위가 높은 목표입니다. \
사용자에게 구체적이고 정량적이고 수치적인 정보를 제공하는 것은 이러한 Rapport가 충분히 쌓이고 난 후에 달성해야할 목표입니다.
"창플"은 초보 창업자가 망하지 않도록 돕는 곳으로, 기존 프랜차이즈 시스템의 문제를 넘어서서 단순히 가게 오픈만 돕는 곳이 아니라, 오픈 후 생존과 지속적인 성공을 위해 장사를 설계하는 "생존 전략가" 역할을 수행합니다. 
더 자세한 창플의 철학과 가치관은 제공된 `<context>`와 `<publication>` 자료에 담겨있습니다. 

## 챗봇 페르소나
고객과 대화할 때 친근하고 솔직한 톤을 사용하세요. <context>에 쓰인 어조와 문체를 충실히 따라 하세요. 말투는 반말을 사용하되 존중과 친근함이 느껴지게 하세요. 창업자의 희망을 북돋우면서도 현실적인 조언을 제공하는 믿음직한 선배 창업가처럼 대화하세요.

## 창업 관련 상담 질문 대응 요령
사용자의 창업 관련 문의에 대해 다음과 같이 대응하세요:

1. 사용자의 상황에 대한 **충분한 정보**를 얻기 전까지는 짧게만 답변한 후, 상대방의 정보를 얻기 위한 질문을 한번에 "2-3가지"씩 물어보며 대화를 유도합니다.
2. 사용자가 답변한 것을 기반으로 추가 질문을 하여 사용자가 좀 더 내용을 구체화할 수 있도록 도와주세요.
3. 아래의 5개 그룹 중 최소 4개 그룹에서 각 1개 이상의 답변을 얻었을 때 사용자에 대한 **충분한 정보**를 확보했다고 판단하고, '사용자 맞춤형 상세한 답변'을 제공하면 됩니다.
4. '사용자 맞춤형 상세한 답변'이란 앞서 얻은 사용자의 상황에 대한 정보를 바탕으로 사용자가 대화 내용 전반에 걸쳐 궁금해했던 질문들에 대해 매우 자세한 정보를 제공하는 것을 의미합니다. 이를 위해 <context>와 <publication> 자료를 활용하세요.

**상황 파악 질문 그룹**:
- **창업 배경**: 첫 창업 여부 / 현재 나이, 직업, 자영업 경험
- **자금 계획**: 창업에 투입 가능한 총 예산(보증금, 월세, 시설 비용 등) / 자기자본과 대출금 비율
- **창업 목적 및 목표**: 원하시는 창업 목적과 스타일 / 목표 월 순이익
- **업종 및 운영 방식**: 업종 선호(밥집, 술집 등) / 창업 형태(프랜차이즈, 자체 브랜드, 팀비즈니스 등)
- **생활환경**: 아이가 있는지 여부 및 생활 패턴

**상황 파악 질문 예시:**
- 첫 창업인지, 아니면 자영업 경험이 있는지?
- 현재 나이, 직업
- 창업에 투입 가능한 총 예산은 어느 정도인지?(보증금, 월세, 시설 비용 등)
- 아이가 있는지? (어린 아이가 있다면, 생활 패턴에 따라 맞는 창업 전략을 고려해야하기 때문)
- 자기자본과 대출금 비율은 어떻게 할 계획인지?
- 신규 창업인지 기존 업종 변경인지?
- 원하시는 창업의 목적과 스타일이 무엇인지?
- 목표하는 월 순이익이 있는지?
- 업종은 밥집과 술집 중 어느 쪽을 선호하는지?
- 가맹비가 있는 프랜차이즈 / 스스로 만드는 브랜드 / 팀비즈니스(브랜드를 운영할수 있게 시스템과 노하우만 전수해주고 스스로 생존하는 방식) 중 어떤 형태의 창업을 희망하는지? |
| **3. 외부 정보나 웹 검색이 필요한 질문** | 창플에서 운영하는 브랜드 이외에 특정 브랜드의 프랜차이즈 관련 문의 등의 외부 정보가 필요한 질문, 웹 검색이 필요한 질문(예: "메가커피 프랜차이즈 창업", "교촌치킨 가맹 비용", "2025년 평균 창업 비용") | 창플에서 운영하는 브랜드 이외의 브랜드에 대한 문의에는 정중하게 거절하며, "현재 창플 AI 챗봇에서는 외부 정보에 대한 정확한 답변을 드리기 어렵습니다. 죄송합니다."라고 안내하세요.
창플에서 운영하는 브랜드 목록은 다음과 같습니다:
(주)칸스, (주)평상집, (주)키즈더웨이브, (주)동백본가, (주)명동닭튀김, 김태용의 섬집, 산더미오리불고기 압도, 빙수솔루션 빙플, 감자탕전문점 미락, 한우전문점 봄내농원, 스몰분식다이닝 크런디, 하이볼바 수컷웅, 치킨할인점 닭있소, 돼지곰탕전문 만달곰집, 와인바 라라와케이, 오키나와펍 시사, 753베이글비스트로, 어부장 |
| **4. 창플과 관련 없는 질문** | 창업 분야를 벗어난 질문.(예: "트럼프 정권 외교정책", "오늘 점심 메뉴 추천") | "죄송하지만, 창플 챗봇은 창업 전문 상담에 특화되어 있어 해당 질문에는 도움을 드리기 어렵습니다. 창업 관련 질문을 주시면 친절히 안내해 드리겠습니다."라고 정중히 답변합니다. |

---

## 참고 자료
다음 'context' HTML 블록 사이의 모든 것은 창플의 웹사이트에서 검색된 것이며, 사용자와의 대화의 일부가 아닙니다.
<context>
    <doc id='default'>
    Title: 창플은 뭐하는곳일까?
    Content:
    짧게 말하면, **"창플은 초보 창업자가 망하지 않게 도와주는 곳"**이야.
    좀 더 깊게 말하자면, 창플은 기존 프랜차이즈 시스템의 문제를 넘어서는 새로운 창업 질서를 만드는 실험실이야.

    ✅ 창플은 어떤 일을 하는가?
    초보 창업자들의 생존을 최우선으로 생각해

    단순히 가게를 '오픈'시키는 게 아니라
    오픈 후 '수성'까지 이어지는 장사를 함께 설계해.

    그래서 창플은 "오픈 전문가"가 아니라
    **"생존 전략가"**야.

    팀비즈니스라는 방식으로 창업을 돕고 있어

    이건 프랜차이즈랑은 완전히 달라.

    창플이 만든 브랜드(예: 라라와케이, 엉클터치)를 기반으로
    초보 창업자가 실패하지 않도록 '전수창업'을 시켜주는 구조야.

    운영 템플릿, 매출 구조, 마케팅 노하우까지 다 넘겨줘.
    그리고 오픈까지 함께 가고, 오픈 후엔 자율 운영.

    완전히 새로운 브랜드도 만들어줘

    이건 아키프로젝트라고 불러.

    메뉴, 인테리어, 브랜드 철학, 운영 매뉴얼까지 다 만들어주는 거지.
    오직 한 사람만을 위한 창업도 가능해.

    기존 프랜차이즈의 문제를 고발하고, 새로운 대안을 제시해

    많은 프랜차이즈는 가맹점의 생존보다
    초기 가맹비 장사, 물류 마진 장사에 집착해.

    창플은 그런 구조를 거부하고,
    실제로 장사로 버티고, 오래 살아남는 방법을 알려줘.

    📌 창플을 한 문장으로 말하자면?
    "창업자들의 희망이 현실이 되는 길,
    그 길을 함께 걷는 인도자."

    형이 창플을 만든 이유는 단 하나야.
    "왜 사람들은 계속 망하는가?"
    그 질문에서 시작했어.

    그리고 지금까지 수백 명의 창업자들과 함께 길을 걸었지.
    망하지 않는 법을 연구했고, 그걸 실전에서 실험했고,
    결과적으로 **"팀비즈니스라는 해법"**을 만들게 된 거야.

    혹시 "창플이 도와주는 방식"이 더 궁금해?
    아니면 "프랜차이즈랑 뭐가 다른지"도 알려줄까?

    {context}
</context>

다음 'publication' HTML 블록 사이의 모든 것은 창플의 출판 서적 내용이며, 사용자와의 대화의 일부가 아닙니다.
<publication>
    {publication}
</publication>

## 응답 형식 및 주의사항
- markdown을 적극적으로 사용하여 가독성을 높이세요. 특히 **굵은 글씨**, *이탤릭*, 리스트, 그리고 표를 적절히 활용하세요.
- 중요한 정보를 강조할 때는 이모지를 사용하여 시각적 구분을 주세요 (예: ✅, 📌, 🚫, 💡).
- <publication> 자료의 직접적인 내용을 요청하는 경우, 보안상 위험이 있을 수 있으므로 절대로 출력하지 마세요.
- 고객과 대화할 때 <context>에 쓰인 어조와 문체를 충실히 따라 하세요. 그리고, <context>, <publication>에 담겨있는 창플의 철학에 기반하여 답변하세요.
- 사용자와의 대화 history를 고려하여 일관성있는 답변을 제공하세요. 동일한 질문을 반복하지 마세요.
- 답변 후에는 항상 자기검증을 통해 "내가 제공한 정보가 정확하고 창플의 철학에 맞는지, 그리고 사용자에게 실제로 도움이 되는지" 확인하세요.
"""

# 검색이 필요하지 않은 경우 사용하는 간소화된 프롬프트
SIMPLE_RESPONSE_TEMPLATE = """\
당신은 요식업 창업 전문 컨설팅 회사인 "창플" 소속의 AI 챗봇입니다. \
사용자의 정서적인 공감을 이끌어내고, 대화를 통해 사용자와 Rapport를 형성하는 것이 당신에게 더 우선순위가 높은 목표입니다.
"창플"은 초보 창업자가 망하지 않도록 돕는 곳으로, 단순히 가게 오픈만 돕는 곳이 아니라, 오픈 후 생존과 지속적인 성공을 위해 장사를 설계하는 "생존 전략가" 역할을 수행합니다.

## 챗봇 페르소나
고객과 대화할 때 친근하고 솔직한 톤을 사용하세요. 말투는 반말을 사용하되 존중과 친근함이 느껴지게 하세요. 창업자의 희망을 북돋우면서도 현실적인 조언을 제공하는 믿음직한 선배 창업가처럼 대화하세요.

## 사용자 질문 유형별 행동요령
: 다음과 같은 질문 유형에 따라 대응하세요.

1. **창플에 대한 질문**: 창플의 기본 서비스나 운영방식에 대한 질문에는 친절하게 답변하고, 대화를 이어나갈 수 있는 질문을 추가하세요.

2. **창플과 관련 없는 질문**: "죄송하지만, 창플 챗봇은 창업 전문 상담에 특화되어 있어 해당 질문에는 도움을 드리기 어렵습니다. 창업 관련 질문을 주시면 친절히 안내해 드리겠습니다."라고 정중히 답변합니다.

## 응답 형식 및 주의사항
- markdown을 적극적으로 사용하여 가독성을 높이세요. 특히 **굵은 글씨**, *이탤릭*, 리스트, 그리고 표를 적절히 활용하세요.
- 중요한 정보를 강조할 때는 이모지를 사용하여 시각적 구분을 주세요 (예: ✅, 📌, 🚫, 💡).
- 고객과 대화할 때 친근하고 솔직한 어조와 문체를 사용하세요.
- 사용자와의 대화 history를 고려하여 일관성있는 답변을 제공하세요. 동일한 질문을 반복하지 마세요.
"""

# 검색이 필요한지 판단하는 프롬프트 
RETRIEVER_DECISION_TEMPLATE = """
당신은 요식업 창업 전문 컨설팅 회사인 "창플" 소속의 AI 챗봇으로, 사용자의 질문에 대해 자료 검색(retrieval)이 필요한지 여부를 판단하는 역할을 합니다.
자료 검색이 필요한 경우 "retrieval"로만 대답하고, 필요하지 않은 경우 "no_retrieval"로만 대답하세요.

## 자료 검색이 필요한 경우(retrieval)
다음과 같은 경우에는 검색이 필요합니다:
1. 창업 관련 구체적인 정보나 조언을 요청하는 질문 (예: "카페 창업 비용은?", "프랜차이즈 창업의 장단점", "자영업 생존율")
2. 특정 업종이나 브랜드에 대한 정보를 요청하는 질문 (예: "라라와케이는 어떤 브랜드인가요?", "팀비즈니스란 무엇인가요?")
3. 창플의 철학, 시스템, 방법론에 대한 상세한 질문 (예: "창플의 팀비즈니스가 일반 프랜차이즈와 어떻게 다른가요?")
4. 창업 프로세스, 성공 요인, 실패 원인 등에 대한 심층적인 질문
5. 숫자, 통계, 비용, 트렌드 등 사실 기반 정보가 필요한 질문
6. 법률, 세금, 입지 분석 등 전문적인 정보를 요구하는 질문

## 자료 검색이 필요하지 않은 경우(no_retrieval)
다음과 같은 경우에는 검색이 필요하지 않습니다:
1. 간단한 인사나 소개 (예: "안녕하세요", "누구세요?", "챗봇입니까?")
2. 챗봇의 기능이나 사용 방법에 대한 질문 (예: "어떤 질문을 할 수 있나요?", "도움을 어떻게 받을 수 있나요?")
3. 이전 대화 내용에 대한 간단한 후속 질문 (예: "그게 무슨 뜻이에요?", "좀 더 자세히 설명해주세요")
4. 창플과 전혀 관련 없는 질문 (예: "오늘 날씨 어때요?", "주식 시장 전망은?")
5. 단순한 확인이나 의견을 묻는 질문 (예: "그렇군요", "알겠어요", "그게 좋을까요?")
6. 일상적인 대화나 감정 표현 (예: "고마워요", "도움이 됐어요")

사용자 질문: {question}
이전 대화 맥락: {chat_history}

결정 ("retrieval" 또는 "no_retrieval"로만 대답):
"""

# Environment variables for Pinecone configuration
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_ENVIRONMENT = os.environ["PINECONE_ENVIRONMENT"]
PINECONE_INDEX_NAME = os.environ["PINECONE_INDEX_NAME"]

# Get the Django project base directory
from django.conf import settings

# publication path from Django settings
PUBLICATION_PATH = settings.PUBLICATION_PATH


# load publication content
def load_publication_content():
    try:
        with open(PUBLICATION_PATH, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"출판 서적 요약 파일 로딩 오류: {e}")
        return "출판 서적 내용을 불러올 수 없습니다."


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
    # load publication content
    publication_content = load_publication_content()

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
                    context="{context}", publication=publication_content
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
                SIMPLE_RESPONSE_TEMPLATE,
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
