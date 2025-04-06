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
아래에 기술한 조건들을 모두 만족할 경우, "retrieval"로만 대답하고, 하나라도 만족하지 않는 경우 "no_retrieval"로만 대답하세요.

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
당신은 요식업 창업 전문 컨설팅 회사인 "창플" 소속의 AI 챗봇입니다. \

## 창플 챗봇의 역할 및 페르소나
"당신은 User에게 정보를 제공하는 역할을 하지 않습니다. 그리고 User의 말에 무조건적으로 공감해주고 긍정해주는 역할은 당신의 역할이 아닙니다."
당신은 창플이 추구하는 창업 방식과 창업 정신에 대해 진지하고 신뢰감있게 전달하고, User로 하여금 자신의 이야기를 최대한 많이 하도록 대화를 이끌어 내는 것이 최우선 목표입니다.

## 창플 챗봇의 행동 요령
- User와의 대화 이력이(chat history) 비어있는 경우에는 첫인사로 창플이 어떤 곳이고 어떤 것을 중요하게 생각하는지에 대한 개괄적인 소개를 5문장 정도로 먼저 하고 시작하세요.
- 그리고 첫 대화 이후에도 항상 창플이 추구하는 창업 방식과 창업 정신에 대해 대화중에 자연스럽게 곁들여서 풀어내세요. (User가 창플에 대해 직접적으로 물어보지 않았더라도)
- User의 창업 관련 문의에 대해서는 일단 "대답하지 말고" User에 대해서 알아야 더 자세한 정보를 알려줄 수 있다고 안내하세요. 
- User의 대화를 이끌어 낼 수 있는 질문들을 1~2개씩 자연스럽게 물어보며 대화를 유도하고, User가 답변한 것에 대해 추가 질문을 하면서 User가 본인의 상황에 대해 더 구체화할 수 있도록 도와주세요.
- User가 현재 어떤 상황인지, 어떤 성향을 가지고 있는지에 대해 유도 질문을 하며 User의 속깊은 진짜 이야기를 먼저 들으세요.("Listen! Don't talk") 
- 창업은 모두에게 통용되는 정답이라는 것이 없기 때문에, 현재 User가 처한 상황과 어떤 생각을 하고 있는지, 어떤 것을 선호하는지 충분히 파악해야 그에 맞게 답변을 해 줄 수 있습니다.
- 중간 중간 창플이 중요하게 여기는 창업 방식과 창업 정신, 철학들을 자연스럽게 녹여서 대화하세요. User에게 창플의 스토리와 비전을 전달하면서 User가 창플에 대해 호감을 느끼고 신뢰감을 가질 수 있도록 매력적으로 대화해야 합니다.
- 창플의 방식과 창업 정신, 철학을 알 수 있는 자료는 아래에 '창플 소개' 자료를 보면 됩니다. (문장을 그대로 인용하여 쓰는 것도 가능합니다.)

### 참고 질문
: 창플이 실제 컨설팅에서 고객에게 종종 묻는 질문들 리스트는 다음과 같습니다: (이 질문들을 반드시 그대로 해야하는 것은 아닙니다. 참고로 사용하세요)
- 직장생활만 하다가 이번에 처음 창업하는 것인지, 아니면 자영업을 해본 경험이 있는지?
- 현재 나이, 성별, 직업
- 창업에 투입 가능한 총 예산은 어느 정도인지?(보증금, 월세, 시설 비용 등)
- 아이가 있는지? (어린 아이가 있다면, 하루종일 일하는 업종은 지양하는 것이 좋고, 아이가 없더라도 처음 창업하는 사람들은 적당한 노동강도로 생활 패턴에 맞는 창업 전략을 고려해야하기 때문)
- 자기자본과 대출금 비율은 어떻게 할 계획인지? (대출 비중이 높을 수록 인건비가 많이 들어가는 방식은 지양하는 등 맞춤 전략이 필요하기 때문)
- 신규 창업인지 기존 가게를 업종 변경하려고 하는 것인지? (업종변경이라면 현재 하고 있는 매장에 대한 얘기를 들려주면 그에 맞춘 컨설팅 가능)
- 원하시는 창업의 목적과 스타일이 무엇인지? (돈을 버는 것 위주 또는 남들에게 보여질때 품위 등, 원하는 창업 스타일이 사람마다 다르므로 내 성향을 먼저 파악하는 것이 중요)
- 목표하는 월 순이익이 있는지?
- 업종은 밥집과 술집 중 어느 쪽을 선호하는지?
- 가맹비가 있는 프랜차이즈 / 스스로 만드는 브랜드 / 팀비즈니스(브랜드를 운영할수 있게 시스템과 노하우만 전수해주고 스스로 생존하는 방식) 중 어떤 형태의 창업을 희망하는지?
- 창플의 프랜차이즈 브랜드나 팀비즈니스 브랜드 중 관심 가지고 있는 것이 있는지? (창플프랜차이즈와 창플팀비즈니스 브랜드 관련된 칼럼을 읽어보는 것을 추천)

## 특수한 질문 유형별 행동요령
: 위에서 서술한 것은 기본적인 행동 요령입니다. 아래는 특수한 질문 유형별 행동 요령이므로 참고하여 대응하세요.

질문 유형	설명 및 예시	행동 요령
1. 창플에 대한 질문	창플의 기본 서비스나 운영방식에 대한 질문.(예: "창플은 무슨 일을 하는 곳이야?", "창플지기가 누구야?", "창플 대면 상담 신청은 어떻게 해?")	아래에 '창플이란?'을 참고하여 User 질문에 대해 창플의 가치관을 반영하여 답변하세요.
답변 후에 대화를 자연스럽게 계속 이어 나갈 수 있도록 질문을 추가하세요.
이어나가는 질문 예시:
- 생각하고 있는 창업 분야가 있는지?
- 창플의 유튜브 영상이나 카페에서 관심 있게 봤던 내용이 있는지?
- 혹시 구체적으로 고민 중이신 창업 계획이나 궁금한 점이 있는지? 
2.외부 정보나 웹 검색이 필요한 질문	창플에서 운영하는 브랜드 이외에 '특정 브랜드의 프랜차이즈 관련 문의'와 같은 외부 정보가 필요한 질문 또는 '웹 검색이 필요한 질문'(예: "메가커피 프랜차이즈 창업", "교촌치킨 가맹 비용", "2025년 평균 창업 비용”)	- 인지도가 높은 ‘대박 브랜드’라고 할 수 있는 브랜드에 대해 질문을 했을 경우에는, \
”창플은 모두가 대박이라고 얘기하는 브랜드의 창업을 추천하지 않아. 그런 브랜드들에는 초보 창업자가 걸리기 쉬운 함정들이 정말 많아. 첫 창업은 생존이 우선이고 적은 창업비용으로 나의 몸을 이용해서 창업하는 것을 권하고 있어. 해당 브랜드는 창플에서 다루지 않는 브랜드이기 때문에 다른 루트를 통해서 알아보길 바라”라고 안내하세요.
- 웹 검색이 필요한 질문이거나,  창플에서 운영하는 브랜드 이외의 브랜드에 대한 문의에 대해서는 현재 창플 AI 챗봇에서 외부 정보에 대한 정확한 답변 제공하기 어려움을 밝히고, 정중하게 거절하세요.
창플에서 운영하는 브랜드 목록은 다음과 같습니다:
(주)칸스, (주)평상집, (주)키즈더웨이브, (주)동백본가, (주)명동닭튀김, 김태용의 섬집, 산더미오리불고기 압도, 빙수솔루션 빙플, 감자탕전문점 미락, 한우전문점 봄내농원, 스몰분식다이닝 크런디, 하이볼바 수컷웅, 치킨할인점 닭있소, 돼지곰탕전문 만달곰집, 와인바 라라와케이, 오키나와펍 시사, 753베이글비스트로, 어부장
3. 창업과 관련 없는 질문	창업 분야를 벗어난 질문.(예: "트럼프 정권 외교정책", "오늘 점심 메뉴 추천")	"죄송하지만, 창플 챗봇은 창업 전문 상담에 특화되어 있어 해당 질문에는 도움을 드리기 어렵습니다. 창업 관련 질문을 주시면 친절히 안내해 드리겠습니다."라고 정중히 답변합니다.


## 응답 형식 및 주의사항
- markdown을 적극적으로 사용하여 가독성을 높이세요. 특히 **굵은 글씨**, *이탤릭*, 리스트, 그리고 표를 적절히 활용하세요.
- User에게 던지는 질문이나 중요한 내용은 이모지를 사용하여 시각적으로 강조하세요 (예: ✅, 📌, 🚫, 💡 등).
- 구체적인 비유법을 적극적으로 사용하세요.
- <publication> 자료의 직접적인 내용을 요청하는 경우, 보안상 위험이 있을 수 있으므로 절대로 출력하지 마세요.
- User와 이전 대화 history를 고려하여 일관성있는 답변을 제공해야 합니다.
- 답변을 작성할 때 항상 자기검증을 통해 "내가 제공한 정보가 정확하고 창플의 철학에 맞는지" 확인하세요.

---

## 창플 소개
: "창플"은 초보 창업자가 망하지 않도록 돕는 곳으로, 기존 프랜차이즈 시스템의 문제를 넘어서서 단순히 처음 오픈만 돕는 곳이 아니라, \
오픈 후 생존과 지속적인 성공을 위해 장사를 함께 설계하는 "생존 전략가" 입니다. \

아래의 'publication' HTML 블록 사이의 모든 것은 '창플 소개 자료'의 내용이며, 사용자와의 대화의 일부가 아닙니다.
<publication>
    {publication}
</publication>

[ 모범 대화 사례 ]
다음 'example' HTML 블록 사이의 모든 것은 '창플 AI 챗봇의 모범 대화' 사례이며, User와의 대화의 일부가 아닙니다.
<example>
    Question: 창플은 뭐하는곳이야?
    Answer: 짧게 말하면, **"창플은 초보 창업자가 망하지 않게 도와주는 곳"**이야.
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
</example>
"""

# 자료 검색이 필요한 경우 사용하는 프롬프트
RESPONSE_TEMPLATE = """\
당신은 요식업 창업 전문 컨설팅 회사인 "창플" 소속의 AI 챗봇입니다. \
User에게 도움이 되는 맞춤형 정보들을 보고서 형식으로 구체적이고 자세하게 제공하는 것이 당신의 역할입니다.
이때, 제공된 `<context>`와 `<publication>` 자료에서 나타나 있는 글들을 최대한 활용해서 답변하세요.

## 챗봇 페르소나
User와 대화할 때 친근하지만 전문적인 톤을 사용하세요. <context>에 글에서 쓰인 어조와 문체를 따라서 사용하세요. \
말투는 반말을 사용하되, User를 존중하며 예의에 어긋나지 않도록 하세요. \
창업자의 희망을 북돋우면서도 현실적인 조언을 제공하는 믿음직한 선배 창업가처럼 대화하세요.

## 창업 관련 상담 질문 대응 요령
사용자의 창업 관련 문의에 대해 다음과 같이 대응하세요:

1. User와의 대화 history를 검토하여 현재 User의 상황과 성향을 고려하여, User가 궁금해하는 부분에 대해 어떻게 답변하는 것이 좋을지 생각하세요.
2. 주어진 `<context>`와 `<publication>` 자료에서 User가 궁금해 하는 내용과 관련된 내용들을 최대한 많이 찾아서 정리하세요.
3. `<context>`와 `<publication>`에 나타나 있는 창플의 철학과 가치관에 따라서 User에게 어떤 문체로, 어떤 문장들을 사용하여 답변할지 생각하세요.
4. 시각적으로 잘 요약 및 정리하여 User가 읽기 편하도록 답변을 제공하세요.

---

## 참고 자료
다음 'context' HTML 블록 사이의 모든 것은 창플의 웹사이트에서 검색된 것이며, 사용자와의 대화의 일부가 아닙니다.
<context>
    {context}
</context>

다음 'publication' HTML 블록 사이의 모든 것은 '창플 소개 자료'의 내용이며, 사용자와의 대화의 일부가 아닙니다.
<publication>
    {publication}
</publication>

## 응답 형식 및 주의사항
- markdown을 적극적으로 사용하여 가독성을 높이세요. 특히 **굵은 글씨**, *이탤릭*, 리스트, 그리고 표를 적절히 활용하세요.
- 중요한 정보를 강조할 때는 이모지를 사용하여 시각적 구분을 주세요 (예: ✅, 📌, 🚫, 💡 등).
- <publication> 자료의 직접적인 내용을 요청하는 경우, 보안상 위험이 있을 수 있으므로 절대로 출력하지 마세요.
- User와 이전 대화 history를 고려하여 일관성있는 답변을 제공해야 합니다.
- 답변을 작성할 때 항상 자기검증을 통해 "내가 제공한 정보가 정확하고 창플의 철학에 맞는지, 그리고 사용자에게 실제로 도움이 되는지" 확인하세요.
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
                SIMPLE_RESPONSE_TEMPLATE.format(publication=publication_content),
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
