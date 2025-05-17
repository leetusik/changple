#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard library imports
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, Optional, Union, cast

os.environ["GRPC_DNS_RESOLVER"] = "native"

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

# Now import Django models after setup
from scraper.models import DisallowedBrands, GoodtoKnowBrands

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
        return f"{title}" if title else "", f"{content}" if content else ""


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


def load_llm(model_name="gemini-2.5-flash-preview-04-17", temperature=0):
    # def load_llm(model_name="gemini-2.0-flash"):
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=temperature)
    return llm


def load_embeddings():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large", chunk_size=200)
    # embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-exp-03-07")
    return embeddings


# -----------------------------------------------------------------------------
# Vector store setup
# -----------------------------------------------------------------------------

api_key = os.environ.get("PINECONE_API_KEY")
environment = os.environ.get("PINECONE_ENVIRONMENT")
index_name = os.environ.get("PINECONE_INDEX_NAME")


@contextmanager
def load_vector_store_retriever(disallowed_brands: list[str]):
    vector_store = PineconeVectorStore(
        index_name=index_name, embedding=load_embeddings(), text_key="text"
    )
    # Dynamically use the fetched list of disallowed brands in the filter
    yield vector_store.as_retriever(
        search_kwargs={
            "k": 4,
            "filter": {"keywords": {"$nin": disallowed_brands}},
        }
    )


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
    disallowed_brands: list[str] = field(default_factory=list)


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
        maximum_five_queries: list[str]

    model = load_llm(
        model_name="gemini-2.5-flash-preview-04-17", temperature=1
    ).with_structured_output(Response)
    generate_queries_system_prompt = """
유저의 질문을 통해 문서를 리트리벌 하기 위해 유저의 질문을 "단어 나열"로 분해하세요.

**구체적인 답변 요령**
첫 번째 단어 나열: 유저가 사용한 단어를 모두 활용한 단어 나열.
두 번째 단어 나열: 유저의 의도를 파악하여 유저가 원하는 정보를 불러오기 위한 창의적 단어 나열.
세 번째 단어 나열(optional): 유저의 질문과 관련된 창플 브랜드이름.
네 번째 단어 나열(optional): 유저의 질문과 관련된 창플 브랜드이름.
다섯 번째 단어 나열(optional): 유저의 질문과 관련된 창플 브랜드이름.

최소 2개, 최대 5개의 단어 나열을 반환하시오.

<창플 브랜드>
{goodto_know_brands}
</창플 브랜드>
    """
    try:
        goodto_know_data = GoodtoKnowBrands.objects.filter(is_goodto_know=True)
        goodto_know_brands = "\n".join(
            [f"{brand.name}: {brand.description}" for brand in goodto_know_data]
        )
    except Exception as e:
        goodto_know_brands = ""

    prompt = generate_queries_system_prompt.format(
        goodto_know_brands=goodto_know_brands
    )

    prompt = [SystemMessage(prompt)] + state["messages"][-5:]
    response = cast(Response, model.invoke(prompt))
    disallowed_brands = list(
        DisallowedBrands.objects.filter(is_disallowed=True).values_list(
            "name", flat=True
        )
    )
    return {
        "retrieve_queries": response["maximum_five_queries"],
        "disallowed_brands": disallowed_brands,
    }


def retrieve_in_parallel(state: AgentState):
    return [
        Send(
            "retrieve_documents", (QueryState(query=query), state["disallowed_brands"])
        )
        for query in state["retrieve_queries"]
    ]


def retrieve_documents(args: tuple[QueryState, list[str]]):
    state, disallowed_brands = args
    with load_vector_store_retriever(disallowed_brands) as retriever:
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


agent = graph.compile()

from IPython.display import Image, display
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles

# display(Image(agent.get_graph().draw_mermaid_png()))
with open("graph.png", "wb") as f:
    f.write(agent.get_graph().draw_mermaid_png())
# print("hi")
