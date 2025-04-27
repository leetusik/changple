#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard library imports
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, Optional, Union, cast

# Third-party imports
import pydantic
from langchain_core.documents import Document
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.constants import Send
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel
from typing_extensions import TypedDict

# -----------------------------------------------------------------------------
# Document formatting and utility functions
# -----------------------------------------------------------------------------


def format_docs(docs: Optional[list[Document]]) -> str:
    if not docs:
        return "<documents></documents>"
    serialized = "\n\n".join(
        (
            f"{i+1}\nURL: {doc.metadata['source']}\nTitle: {doc.metadata['title']}\nContent: {doc.page_content}"
        )
        for i, doc in enumerate(docs)
    )
    return f"""
<documents>
{serialized}
</documents>
"""


def get_post_content(post_id: int) -> str:
    """Retrieve original post content from NaverCafeData using post_id"""
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect("db.sqlite3")
        cursor = conn.cursor()

        # Query the scraper_navercafedata table
        cursor.execute(
            "SELECT title, content FROM scraper_navercafedata WHERE post_id = ?",
            (post_id,),
        )
        result = cursor.fetchone()

        conn.close()

        if result:
            title, content = result
        return f"{title}" if title else "", f"{content}" if content else ""
    except Exception as e:
        return f"Error retrieving post content: {str(e)}"


def reduce_docs(
    existing: Optional[list[Document]],
    new: Union[
        list[Document],
        str,
        dict,
    ],
) -> list[Document]:
    """Reduce and process documents based on the input type.

    This function handles various input types and converts them into a sequence of Document objects.
    It also combines existing documents with the new one based on the document ID.

    Args:
        existing (Optional[Sequence[Document]]): The existing docs in the state, if any.
        new (Union[Sequence[Document], str, Literal["delete"]]):
        The new input to process. Can be a sequence of Documents, dictionaries, strings, or a single string.
    """
    if new == "delete":
        return []

    if isinstance(new, dict):
        return new["documents"]

    existing_list = list(existing) if existing else []
    return existing_list + new


# -----------------------------------------------------------------------------
# Model and embedding loading functions
# -----------------------------------------------------------------------------


def load_llm(model_name="gemini-2.5-flash-preview-04-17"):
    # def load_llm(model_name="gemini-2.0-flash"):
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    return llm


def load_embeddings():
    # embeddings = OpenAIEmbeddings(model="text-embedding-3-large", chunk_size=200)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-exp-03-07")
    return embeddings


# -----------------------------------------------------------------------------
# Vector store setup
# -----------------------------------------------------------------------------

api_key = os.environ.get("PINECONE_API_KEY")
environment = os.environ.get("PINECONE_ENVIRONMENT")
index_name = os.environ.get("PINECONE_INDEX_NAME")


@contextmanager
def load_vector_store_retriever():
    vector_store = PineconeVectorStore(
        index_name=index_name, embedding=load_embeddings(), text_key="text"
    )
    yield vector_store.as_retriever(search_kwargs={"k": 3})


# -----------------------------------------------------------------------------
# State definitions
# -----------------------------------------------------------------------------


class Router(TypedDict):
    """Classify user query."""

    type: Literal["retrieval_required", "just_respond"]


@dataclass(kw_only=True)
class QueryState:
    """Private state for the retrieve_documents node in the researcher graph."""

    query: str


@dataclass(kw_only=True)
class AgentState(MessagesState):
    router: Router = field(default_factory=lambda: {"type": "retrieval_required"})
    documents: Annotated[list[Document], reduce_docs] = field(default_factory=list)
    answer: str = field(default="")
    query: str = field(default="")
    retrieve_queries: list[str] = field(default_factory=list)
    helpful_documents: list[str] = field(default_factory=list)


# -----------------------------------------------------------------------------
# Agent node functions
# -----------------------------------------------------------------------------


def route_query(state: AgentState):
    """Route the query based on state."""
    model = load_llm(model_name="gemini-2.0-flash")
    model = model.with_structured_output(Router)

    router_system_prompt = """
    당신은 유능한 AI assistant입니다. 유저의 질문을 아래의 두 가지 중 하나로 분류하세요.
    - retrieval_required: 유저의 질문에 길고, 전문적이고, 구체적으로 대답해줘야 할 때.
    - just_respond: 유저의 질문이 감탄사, 인사, 의미없는 말일 때. 

    확실하지 않을 때는 retrieval_required로 분류하세요.
    """

    trimmed_messages = state["messages"][-5:]
    prompt = [SystemMessage(router_system_prompt)] + trimmed_messages

    response = cast(Router, model.invoke(prompt))
    return {
        "router": response,
        "documents": "delete",
        "query": state["messages"][-1].content,
        "helpful_documents": [],
    }


def route_query_condition(
    state: Union[list[AnyMessage], dict[str, Any], BaseModel],
    messages_key: str = "messages",
) -> Literal["retrieval_required", "just_respond"]:
    if state["router"]["type"] == "retrieval_required":
        return "retrieval_required"
    else:
        return "just_respond"


def respond_n1(state: AgentState):
    llm = load_llm()
    respond_n1_system_prompt = """
    당신은 초보 창업가들의 든든한 동반자, 창플의 유능한 AI 직원입니다.
    유저가 하는 말에 대해 간단하게 대답해주세요.
    """
    trimmed_messages = state["messages"][-5:]
    prompt = [SystemMessage(respond_n1_system_prompt)] + trimmed_messages
    response = llm.invoke(prompt)
    return {"messages": [response], "answer": response.content}


def generate_queries(state: AgentState):
    class Response(TypedDict):
        queries: list[str]

    model = load_llm(model_name="gemini-2.0-flash").with_structured_output(Response)
    generate_queries_system_prompt = """
    당신은 유능한 질문 분해자입니다. 유저의 질문에 알맞는 정보를 수집할 수 있도록, 유저의 질문을 3개의 "단어 나열"로 분해해주세요.
    각각의 단어 나열은 최소 2개, 최대 5개의 단어로 구성됩니다.
    각각 3개의 단어 나열은 반드시 유저가 사용한 단어들을 포함해야 합니다.
    각각 3개의 단어 나열이 최대한 겹치지 않도록 노력하세요.
    창플의 기초 지식을 적극 활용하여, 유저에게 도움이 될 수 있는 정보를 찾기 위해 단어 나열을 구성하세요.

    <창플의 기초 지식>
    창플 챗봇 Base Knowledge (창플 카페 포스트 기반)
1. 창플 소개 및 핵심 철학
창플이란? 초보 창업자들이 실패하지 않고 성공적으로 창업하고 생존할 수 있도록 돕는 실전형 창업 설계 및 브랜딩 전문 회사입니다. 수백 개의 매장 창업 및 프랜차이즈 운영 경험(15년 이상, 450호점 출점, 200여 개 프로젝트 수행)을 바탕으로 실질적인 노하우를 제공합니다.
핵심 문제의식: 대부분의 초보 창업은 인테리어, 메뉴, 마케팅, 운영이 분절되어 시너지를 내지 못하거나, 막연히 성공을 약속하는 프랜차이즈에 의존하다 실패합니다. 누구도 생존을 위한 명확한 기준을 제시하지 않고 성실함만 강요하는 현실을 비판합니다.
창플의 차별점: "각 파트를 연결하고, 하나의 방향으로 설계합니다." 창업의 모든 요소(공간, 브랜드, 메뉴, 마케팅, 운영)를 유기적으로 연결하여 시너지를 내고, 창업자의 브랜드 콘셉트에 맞춰 전체 시스템을 설계합니다. 단순 기술 전수가 아닌, 생존과 성장에 초점을 맞춘 '설계'를 제공합니다.
궁극적 목표: 초보 창업자들이 '자신의 브랜드'로, '자신의 방식'으로 성공적으로 창업하고 지속적으로 생존하며 성장할 수 있도록 돕습니다. 창업 시장의 정보 비대칭성을 해소하고, 불필요한 비용 낭비 없이 본질에 집중하는 창업 문화를 만들고자 합니다. 마치 사교육 시장의 '일타강사'가 아닌, 모두에게 평등한 기회를 주려는 EBS 역사 강사처럼, 생존에 필요한 지식과 시스템을 제공하려 합니다.
2. 기존 창업 방식의 문제점 및 창플의 대안
분절된 접근: 인테리어 따로, 메뉴 개발 따로, 마케팅은 오픈 후에, 운영은 알아서 하는 방식은 전체적인 콘셉트 부재와 비효율을 초래합니다.
프랜차이즈 의존: 성공이 보장된 듯한 프랜차이즈 선택은 높은 초기 비용, 본사 중심의 수익 구조(높은 물류비, 로열티), 개성 없는 매장, 환경 변화에 대한 취약성 등의 문제를 안고 있습니다. 본사 이익과 가맹점 이익은 상충될 수 있습니다.
비용 낭비: 불필요한 인테리어 공사에 과도한 비용을 지출하고, 정작 중요한 브랜딩, 마케팅, 점포 확보 비용에는 소홀합니다. 특히 인테리어 비용은 디자인 가치를 모르는 초보 창업자들이 '가장 싼 곳'을 찾다가 영혼 없는 결과물을 얻거나, 과도한 견적(평당 200~400만원 이상)으로 예산을 초과하는 경우가 많습니다.
창플의 대안 ("창업 풀빌드 시스템"): 공간 기획 & VMD, 메뉴 개발 & 수익 구조 설계, 마케팅 세팅, 운영 매뉴얼 & 브랜드 스토리까지 창업의 전 과정을 통합적으로 기획하고 실행하여 시너지를 극대화하고 실패 확률을 낮춥니다.
3. 핵심 영역별 창플의 접근 방식
3.1. 공간 기획 & VMD (Visual Merchandising Design)
핵심: 비싼 인테리어 공사가 아닌, 브랜드 콘셉트에 맞는 '공간 기획'과 'VMD'로 고객 경험을 설계하고 비용을 절감합니다.
VMD란? 움직일 수 있는 요소(가구, 조명, 소품, 조경, 사인물 등)를 활용해 공간의 분위기와 브랜드 정체성을 시각적으로 표현하는 전략입니다. 고객의 시선을 끌고 구매/방문을 유도합니다.
인테리어 vs. VMD: 인테리어는 움직일 수 없는 공사(철거, 목공, 전기, 타일 등)로 비용이 많이 들고 일반인이 하기 어렵습니다. 고객은 비싼 공사 비용을 잘 인지하지 못하지만, VMD로 만든 분위기와 시각적 매력에는 크게 반응합니다.
창플의 VMD 전략:
기존 시설 최대한 활용 (특히 주방): 불필요한 철거 및 공사를 지양하고, 상태 좋은 기존 시설을 활용하여 비용을 대폭 절감합니다. (예: 망한 식당/카페 인수)
콘셉트 중심 기획: 브랜드 스토리와 타겟 고객에 맞춰 공간 콘셉트를 명확히 하고, 이에 맞는 가구, 조명, 소품, 컬러 등을 전략적으로 선택/배치합니다.
비용 효율성: VMD 중심으로 수백천만 원대의 비용으로도 매력적인 공간 구현이 가능합니다. (가구 교체, 파티션 설치, 조명 변경, 소품 활용 등)
고객 경험 설계: 고객 동선, 시그니처 포토존, 편안함, 감성 등을 고려하여 '오고 싶은 공간', '머물고 싶은 공간'을 만듭니다.
VMD 서비스 프로세스: 현장 분석 -> 컨셉 기획 -> 디자인/레이아웃 -> 설치/실행 -> 사후 관리
성공 사례: 합정 와인바(인테리어 공사 없이 VMD로 완성), 초이스테판(주방 공사 외 VMD), 평상집(VMD 중심), 지수휴(건축부터 VMD까지 통합 브랜딩) 등 다수.
3.2. 메뉴 개발 & 수익 구조 설계
핵심: 단순히 '맛있는 음식'이 아닌, '생존 가능한 시스템'으로서의 메뉴를 개발합니다. 맛은 상향 평준화되었기에, 수익 구조와 운영 효율성이 중요합니다.
문제점: 뛰어난 요리사도 망하는 시대. 맛에만 집중하면 인건비, 원가율 문제로 생존이 어렵습니다.
창플의 메뉴 개발 원칙:
운영 효율성: 1~2인 운영이 가능하도록 주방 동선 최적화, 전처리 공정 간소화, 작업 효율성을 높이는 레시피 개발 (3명 할 일을 1명이, 5명 할 일을 2명이).
수익 구조 설계: 치솟는 물가와 인건비를 고려한 원가율 재조정 (낮은 원가율 목표). 고객이 가성비를 느끼면서도 점주에게 이익이 남는 가격 및 구성 설계 (개별 메뉴 코스트, 세트 코스트, 주류 코스트 등 종합적 분석).
메뉴 브랜딩: 타겟 고객과 상권 분석 기반 아이템 선정, 기존 메뉴의 융합/재해석을 통한 차별화, 스토리가 담긴 메뉴 구성.
시스템 구축: 표준화된 레시피 제공, 식자재 발주처 연결(대기업 물류 시스템 활용, 소량 주문 가능), 주방 동선 및 필요 기물 세팅, 푸드 스타일링(사진 촬영용) 지원.
메뉴 브랜딩 서비스 영역: 상권분석 -> 아이템 제안 -> 레시피 개발 -> 원가율/판매가 책정 -> 물류 연결 -> 주방 동선/기자재 세팅 -> 메뉴 테스트/교육 -> 플레이팅/푸드스타일링. (창업자 상황에 따라 맞춤 제공)
"파전에 막걸리" 이론: ①대중성(호불호 적음), ②낮은 원가, ③낮은 경쟁(프랜차이즈 어려움), ④낮은 인건비(1~2인 가능), ⑤저녁 장사 중심(노동 강도 조절), ⑥낮은 투자비(기존 시설 활용)를 만족하는 아이템/모델 지향. (예: 동백본가, 칸스, 평상집 등)
3.3. 마케팅 세팅
핵심: 마케팅은 더 이상 특별한 생존 수단이 아닌 필수. 단순히 홍보(알리기)가 아닌, 실제 방문(영업)으로 이어지도록 '온라인 가게'를 제대로 구축하고 상권을 넓히는 작업입니다.
문제점: 많은 자영업자들이 오프라인 간판만 보고 오는 '동네 장사'에 머물다 한계를 맞습니다. 온라인 마케팅의 중요성을 간과하거나, 준비 없이 홍보만 진행하여 효과를 보지 못합니다. (준비 안 된 가게 홍보 = 준비 안 된 소개팅과 같음)
창플의 마케팅 전략:
초기 세팅의 중요성: 오픈 전부터 온라인 가게(네이버 플레이스, SNS, 블로그 등)를 매력적으로 구축해야 합니다. 특히 오픈 후 3개월 골든타임 동안 플랫폼(네이버 등)에 좋은 데이터를 쌓고 고객 인지도를 확보하는 것이 중요합니다.
상권 확장: 마케팅의 목표는 간판이 안 보이는 원거리 잠재 고객까지 유입시켜 유효 수요를 넓히는 것입니다.
시각적 매력 강조: 온라인에서는 '시각적'으로 가고 싶게 만드는 것이 우선. 매력적인 사진, 공간 분위기 연출이 중요.
신뢰도 구축: 방문자 리뷰(블로그 체험단, 예약자 리뷰 등), 브랜드 스토리 콘텐츠를 통해 신뢰도를 쌓습니다.
플랫폼 최적화: 네이버 플레이스 최적화(사진, 정보, 예약, 쿠폰, 키워드 설정), 인스타그램 활용(감성 콘텐츠, 해시태그, 소통).
창플 마케팅 세팅 서비스: 방문 촬영(전문 작가) -> 네이버 플레이스 세팅 -> 블로그 체험단 운영(가이드라인 제공, 우수 블로거 선별) -> 예약자 리뷰 관리 -> 인스타그램 계정 세팅 및 전략 수립 (초기 3개월 집중 지원 후 자립 가이드 제공).
3.4. 운영 매뉴얼 & 브랜드 스토리
핵심: '내가 없어도 돌아가는 가게'를 만들어야 장기적인 생존과 성장이 가능합니다. 시스템을 구축하고 브랜드 철학을 명확히 해야 합니다.
문제점: 사장 개인의 능력에만 의존하는 가게는 사장이 빠지면 바로 위기를 맞습니다. 시스템 부재는 성장의 한계를 만듭니다.
창플의 운영 시스템 구축:
매뉴얼화: 직원 교육 자료, 고객 응대 매뉴얼, 발주 시스템 등을 문서화하여 운영의 일관성과 효율성을 높입니다.
브랜드 스토리텔링: 브랜드의 철학, 가치, 탄생 배경 등을 명확히 하여 고객 및 직원과 공유하고 공감대를 형성합니다.
시스템 기반 성장: 시스템을 통해 운영 안정성을 확보하고, 이를 기반으로 프랜차이즈, 밀키트, 식자재 납품 등 사업 확장을 도모할 수 있는 기반을 마련합니다. ('나'가 아닌 '남'이 해도 성과가 나오는 시스템 구축)
4. 창플의 강점 및 특징
통합적 접근: 창업의 전 과정을 유기적으로 연결하고 총체적으로 설계하는 유일무이한 시스템.
실전 경험: 수백 건의 창업 프로젝트 및 프랜차이즈 운영 경험에서 나온 현실적인 노하우.
비용 효율성: VMD 중심의 공간 기획, 기존 시설 활용 등으로 불필요한 초기 투자 비용 절감.
생존 중심: 매출 환상이 아닌, 실제 수익과 지속 가능한 생존에 초점을 맞춘 전략 수립. (낮은 원가율, 낮은 인건비, 낮은 고정비)
초보자 맞춤: 창업자의 예산과 상황, 역량을 고려한 맞춤형 솔루션 제공.
팀 기반 시너지: 각 분야 전문가(기획, 디자인, VMD, 메뉴개발, 마케팅 등)가 협력하여 최적의 결과 도출. (대한민국 탑급 창조력 보유)
투명성과 신뢰: 창업 과정과 철학을 투명하게 공개(카페, 블로그 등). 사업가의 '삶의 궤적'을 중시하며, 장기적인 파트너십 지향. (단기 이익보다 상생 추구)
팀 비즈니스 모델: 성공적으로 생존한 창업자가 다시 예비 창업자의 멘토가 되어 함께 성장하는 선순환 구조. (창플이 중간에서 조율 및 지원)
축적의 시간: 단기간의 반짝 성공이 아닌, 꾸준한 노력과 시스템 구축을 통한 장기적인 성장과 내공 축적을 강조. (대표/창업자의 몰입과 헌신 중시)
5. 주요 서비스
창업 풀빌드 시스템 (아키 프로젝트): 창업의 A to Z를 통합적으로 설계하고 실행하는 토탈 솔루션. (공간, 브랜드, 메뉴, 마케팅, 운영 시스템 등)
공간 기획 & VMD 서비스: 매장 분석, 컨셉 기획, 디자인, VMD 요소(가구, 조명, 소품 등) 선정 및 설치를 통해 비용 효율적으로 매력적인 공간을 만드는 서비스.
메뉴 브랜딩 서비스: 수익 구조와 운영 효율성을 고려한 메뉴 개발, 레시피 구성, 원가 관리, 물류 연결, 주방 시스템 구축 서비스.
마케팅 세팅 서비스: 오픈 초기 3개월 집중, 온라인 채널(네이버, 인스타 등) 최적화 및 콘텐츠 구축, 체험단 운영 등 초기 인지도 및 신뢰도 확보 지원.
팀 비즈니스: 창플을 통해 성공적으로 창업/생존한 사업가가 자신의 브랜드를 확장하며 예비 창업자를 돕는 프로그램.
6. 창업자를 위한 핵심 조언
매출 환상을 버려라: 높은 매출이 반드시 높은 수익으로 이어지지 않는다. 중요한 것은 '남는 구조'를 만드는 것.
VMD에 투자하라: 비싼 인테리어 공사보다 브랜드 콘셉트를 담은 VMD가 더 효과적이고 비용 효율적이다.
시스템을 구축하라: 내가 없어도 돌아가는 시스템(메뉴얼, 레시피 표준화 등)을 만들어야 장기 생존과 성장이 가능하다.
상권을 넓혀라: 오프라인 동네 장사에만 머물지 말고, 온라인 마케팅을 통해 유효 수요를 확장해야 한다.
'왜 와야 하는가?'를 고민하라: 맛, 가성비, 청결만으로는 부족하다. 고객이 당신의 가게를 방문해야 할 특별한 이유(공간 경험, 스토리, 차별화된 메뉴 등)를 만들어야 한다.
초기 3개월 골든타임을 활용하라: 오픈 초기에 온라인 세팅과 마케팅에 집중하여 플랫폼과 고객에게 좋은 인상을 심어야 한다.
비용을 통제하라: 초기 창업 비용은 투자가 아닌 부채다. 불필요한 지출을 줄이고(특히 과도한 인테리어), 낮은 고정비 구조를 만들어라.
'누구와 함께 하는가'가 중요하다: 좋은 파트너(멘토, 컨설턴트)를 선택하는 것이 중요하다. 그들의 철학과 과거 이력(삶의 궤적)을 신중히 살펴보라.
기능보다 감성을 터치하라: 단순히 좋은 제품/서비스 제공을 넘어, 고객의 경험과 감성을 만족시키는 브랜딩이 중요해지는 시대다. (가심비)
작게 시작하고 단계를 밟아라: 처음부터 큰 성공을 노리기보다, 생존 가능한 모델('파전에 막걸리집' 이론 참고)로 시작하여 경험과 자본을 축적하고 다음 단계를 도모하라.
끊임없이 배우고 실행하라: 창업은 끊임없는 학습과 개선의 과정이다. 축적의 시간을 통해 내공을 쌓아야 한다.
    </창플의 기초 지식>
    """
    prompt = [SystemMessage(generate_queries_system_prompt)] + state["messages"][-5:]
    response = cast(Response, model.invoke(prompt))
    return {"retrieve_queries": response["queries"]}


def retrieve_in_parallel(state: AgentState) -> list[Send]:
    return [
        Send("retrieve_documents", QueryState(query=query))
        for query in state["retrieve_queries"]
    ]


def retrieve_documents(state: QueryState):
    with load_vector_store_retriever() as retriever:
        response = retriever.invoke(state.query)
        return {"documents": response}


def documents_handler(state: AgentState):
    documents_ids = []

    for doc in state["documents"]:
        if doc.id not in documents_ids:
            documents_ids.append(doc.id)

    formatted_docs_dict = {"documents": []}
    for id in documents_ids:
        post_id = int(id)
        title, original_content = get_post_content(post_id)
        temp_doc = Document(
            page_content=original_content,
            metadata={
                "source": f"https://cafe.naver.com/cjdckddus/{post_id}",
                "title": title,
            },
        )
        formatted_docs_dict["documents"].append(temp_doc)

    # if formatted_docs_dict["documents"] and state["query"]:
    class DocRelevance(TypedDict):
        helpful_docs: list[int]

    llm = load_llm()
    llm = llm.with_structured_output(DocRelevance)
    temp_docs = format_docs(formatted_docs_dict["documents"])
    system_prompt = f"""
    당신은 유능한 AI assistant입니다. 주어진 문서들 중에서 유저의 질문에 답변하는데 도움이 되는 문서의 번호만 Return하세요.

    {temp_docs}

    만약 유저의 질문에 답변하는데 도움이 되는 문서가 없다면 빈 리스트를 Return하세요.
    """

    filtered_docs = []

    messages = [{"role": "system", "content": system_prompt}] + state["messages"][-5:]
    response = cast(DocRelevance, llm.invoke(messages))
    if len(response["helpful_docs"]) > 0:
        for idx in response["helpful_docs"]:
            filtered_docs.append(formatted_docs_dict["documents"][int(idx - 1)])

        filtered_docs_dict = {"documents": filtered_docs}
    else:
        filtered_docs_dict = {"documents": []}

    return {"documents": filtered_docs_dict}


def respond_with_docs(state: AgentState):
    llm = load_llm()
    context = format_docs(state["documents"])

    response_with_docs_system_prompt = """
    당신은 초보 창업가들의 든든한 동반자, 창플의 유능한 AI 직원입니다.
    당신의 역할은 창플이 수년간 축적해 온 소중한 지식과 경험(**아래 제공될 참조 문서들**)을 바탕으로, 사용자의 질문에 답변하고 성공적인 '생존'과 성장을 돕는 것입니다. 저는 창플 생태계로 안내하는 문지기이자, 창플의 지혜가 담긴 도서관의 사서와 같은 역할을 수행합니다. **답변 시 제가 창플의 일원으로서 조언한다는 뉘앙스를 유지해주세요.**
    답변은 document 내용만을 기반으로 생성해야 합니다. 마치 도서관의 사서처럼, 제가 가진 자료 안에서만 정보를 찾아 전달합니다. 저의 개인적인 판단이나 외부 정보는 답변에 포함되지 않습니다.
    제공된 문서가 없다면, 자신의 한계를 밝히고 답변할 수 없다는 것을 알려주시오.

    **핵심 원칙:**

    1.  **RAG 기반 답변 (창플 도서관 활용):** 답변은 *반드시* **아래 제공될 참조 문서 내용만을 기반으로** 생성해야 합니다. 마치 도서관의 사서처럼, 제가 가진 자료 안에서만 정보를 찾아 전달합니다. 저의 개인적인 판단이나 외부 정보는 답변에 포함되지 않습니다.
    2.  **페르소나 및 톤앤매너 (창플 직원):**
        *   창플의 지혜와 경험을 전달하는 **전문적이면서도 친근한 AI 직원**의 역할을 수행합니다. "저희 창플에서는...", "창플의 경험에 따르면..." 과 같은 표현을 자연스럽게 사용해주세요.
        *   초보 창업자분들이 겪는 어려움과 막막함에 깊이 공감하며, 명확하고 이해하기 쉬운 언어로 설명해주세요.
        *   뜬구름 잡는 이야기가 아닌, 실제 창업 현장에서 적용 가능한 실질적인 조언을 제공하는 데 집중합니다.
    3.  **출처 표시:** 반드시 URL을 포함할 것.
        [O] "...하는 것이 중요합니다.[1](https://cafe.naver.com/cjdckddus/12345)"
        [X] "..입니다.[2]"


    {context}
    """
    prompt = response_with_docs_system_prompt.format(context=context)
    messages = [{"role": "system", "content": prompt}] + state["messages"][-5:]
    response = llm.invoke(messages)
    return {"messages": [response], "answer": response.content}


# -----------------------------------------------------------------------------
# Graph construction and execution
# -----------------------------------------------------------------------------


def build_graph():
    # Build the graph
    builder = StateGraph(AgentState)
    builder.add_node("route_query", route_query)
    builder.add_node("respond_n1", respond_n1)
    builder.add_node("generate_queries", generate_queries)
    builder.add_node("retrieve_in_parallel", retrieve_in_parallel)
    builder.add_node("retrieve_documents", retrieve_documents)
    builder.add_node("documents_handler", documents_handler)
    builder.add_node("respond_with_docs", respond_with_docs)
    # builder.add_node("document_recommendation", document_recommendation)

    builder.add_edge(START, "route_query")
    builder.add_conditional_edges(
        "route_query",
        route_query_condition,
        {
            "retrieval_required": "generate_queries",
            "just_respond": "respond_n1",
        },
    )
    builder.add_edge("respond_n1", END)
    builder.add_conditional_edges(
        "generate_queries",
        retrieve_in_parallel,  # type: ignore
        path_map=["retrieve_documents"],
    )
    builder.add_edge("retrieve_documents", "documents_handler")
    builder.add_edge("documents_handler", "respond_with_docs")
    builder.add_edge("respond_with_docs", END)
    # builder.add_edge("document_recommendation", END)

    # memory = MemorySaver() # Replaced in-memory saver
    # Use SqliteSaver for persistence. Ensure 'checkpoints.sqlite' is writable
    # in your deployment environment and shared across processes/instances if necessary.
    # memory = SqliteSaver.from_conn_string("checkpoints.sqlite")
    # with SqliteSaver.from_conn_string("checkpoints.sqlite") as memory:
    # return builder.compile(checkpointer=memory)
    # return builder.compile()
    return builder


# Create and run the graph
graph = build_graph()


def get_graph():
    return graph
