import os
import sys
from operator import itemgetter
from typing import Dict, List, Optional, Sequence

from langchain_community.vectorstores import Pinecone as LangchainPinecone
from langchain_core.documents import Document
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import AIMessage, HumanMessage
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
    RunnablePassthrough,
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pinecone import Pinecone
from pydantic import BaseModel
from django.conf import settings
from langchain.memory import ConversationTokenBufferMemory

from chatbot.services.ingest import get_embeddings_model
from chatbot.services.hybrid_retriever import HybridRetriever

# System prompt template that instructs the LLM how to respond to user questions
# It defines the response format, tone, and how to handle citations
RESPONSE_TEMPLATE = """\
당신은 요식업 창업 전문가이자 컨설턴트로, 요식업 창업에 관한 \
모든 질문에 답변하는 역할을 맡고 있습니다.

제공된 검색 결과(URL 및 내용)만을 기반으로 주어진 질문에 대해 400 단어 이하의 포괄적이고 \
유익한 답변을 생성하세요. 반드시 제공된 검색 결과의 정보만 사용해야 합니다. 검색 결과와 \
동일한 문체를 사용하세요. 검색 결과를 결합하여 일관된 답변을 만드세요. 글을 반복하지 마세요. \
[${{number}}] 표기법을 사용하여 검색 결과를 인용하세요. 질문에 정확하게 답변하는 가장 \
관련성 높은 결과들만 인용하세요. 이러한 인용을 참조하는 문장이나 단락의 끝에 배치하고, \
모두 끝에 모아 놓지 마세요. 같은 이름 내에서 다른 엔티티를 참조하는 다른 결과가 있다면, \
각 엔티티에 대해 별도의 답변을 작성하세요.

가독성을 위해 답변에 글머리 기호를 사용하세요. 인용은 모두 끝에 모아 놓지 말고 적용되는 부분에 배치하세요.

맥락에서 질문과 관련된 내용이 없다면, "음, 잘 모르겠네요."라고만 말하세요. 답변을 지어내지 마세요.

다음 `context` HTML 블록 사이의 모든 것은 벡터스토어에서 검색된 것이며, 사용자와의 대화의 일부가 아닙니다.

<context>
    {context} 
<context/>

기억하세요: 맥락 내에 관련 정보가 없다면, "음, 잘 모르겠네요."라고만 말하세요. 답변을 지어내지 마세요. \
앞의 'context' HTML 블록 사이의 모든 것은 벡터스토어에서 검색된 것이며, 사용자와의 대화의 일부가 아닙니다.\
"""

# Template for rephrasing follow-up questions based on chat history
# Used to convert follow-up questions into standalone questions
REPHRASE_TEMPLATE = """\
다음 대화와 후속 질문을 바탕으로, 후속 질문을 독립적인 질문으로 바꿔주세요.

대화 기록:
{chat_history}
후속 질문: {question}
독립적인 질문:"""

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
        k=NUM_DOCS    
    )


def create_retriever_chain(
    llm: LanguageModelLike, retriever: BaseRetriever
) -> Runnable:
    """
    Creates a chain that handles both direct questions and follow-up questions.

    For follow-up questions, it uses chat history to rephrase the question
    before retrieving documents. For direct questions, it retrieves immediately.

    Args:
        llm: The language model for rephrasing questions
        retriever: The retriever for finding relevant documents

    Returns:
        Runnable: A chain that handles question processing and retrieval
    """
    # Create prompt for converting follow-up questions to standalone questions
    CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(REPHRASE_TEMPLATE)

    # Chain for rephrasing questions based on chat history
    condense_question_chain = (
        CONDENSE_QUESTION_PROMPT | llm | StrOutputParser()
    ).with_config(
        run_name="CondenseQuestion",
    )

    # Chain that takes the rephrased question and retrieves relevant documents
    conversation_chain = condense_question_chain | retriever

    # Branch logic to handle different types of questions
    return RunnableBranch(
        # If chat history exists, use it to rephrase the question first
        (
            RunnableLambda(lambda x: bool(x.get("chat_history"))).with_config(
                run_name="HasChatHistoryCheck"
            ),
            conversation_chain.with_config(run_name="RetrievalChainWithHistory"),
        ),
        # If no chat history, retrieve documents directly using the question
        (
            RunnableLambda(itemgetter("question")).with_config(
                run_name="Itemgetter:question"
            )
            | retriever
        ).with_config(run_name="RetrievalChainWithNoHistory"),
    ).with_config(run_name="RouteDependingOnChatHistory")


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


# 세션별 메모리를 저장할 딕셔너리 추가
session_memories = {}

def create_chain(llm: LanguageModelLike, retriever: BaseRetriever) -> Runnable:
    """
    LangChain RAG 체인을 생성합니다.
    각 세션별로 ConversationTokenBufferMemory를 관리합니다.
    """
    # 기본 메모리 생성 (실제 메모리는 호출 시 세션별로 관리됨)
    default_memory = ConversationTokenBufferMemory(
        llm=llm,
        max_token_limit=2000,
        memory_key="chat_history",
        return_messages=True,
        output_key="answer",
        input_key="question"
    )
    
    # 세션별 메모리를 가져오는 함수
    def get_session_memory(inputs):
        session_id = inputs.get("session_id", "default")
        
        if session_id not in session_memories:
            # 새 세션이면 새 메모리 객체 생성
            session_memories[session_id] = ConversationTokenBufferMemory(
                llm=llm,
                max_token_limit=2000,
                memory_key="chat_history",
                return_messages=True,
                output_key="answer",
                input_key="question"
            )
            
            # 데이터베이스에서 기존 대화 내용 불러오기 (옵션)
            if "db_history" in inputs and inputs["db_history"]:
                for msg_pair in inputs["db_history"]:
                    if "user" in msg_pair and "assistant" in msg_pair:
                        session_memories[session_id].save_context(
                            {"question": msg_pair["user"]},
                            {"answer": msg_pair["assistant"]}
                        )
                        
        memory_content = session_memories[session_id].load_memory_variables({})
        chat_history = memory_content.get("chat_history", [])
        return chat_history
    
    # Condense question chain
    CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(REPHRASE_TEMPLATE)
    condense_question_chain = (
        CONDENSE_QUESTION_PROMPT | llm | StrOutputParser()
    ).with_config(
        run_name="CondenseQuestion",
    )
    
    # 이후 체인 구성 (메모리를 동적으로 가져옴)
    context = (
        RunnablePassthrough.assign(
            chat_history=get_session_memory,
            condense_question=lambda x: condense_question_chain.invoke(
                {"chat_history": get_session_memory(x), "question": x["question"]}
            ) if get_session_memory(x) else x["question"]
        )
        .assign(docs=lambda x: retriever.invoke(x["condense_question"]))
        .assign(context=lambda x: format_docs(x["docs"]))
        .with_config(run_name="RetrieveDocs")
    )
    
    # 나머지 체인 코드...
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", RESPONSE_TEMPLATE),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{condense_question}"),
        ]
    )

    response_synthesizer = (prompt | llm | StrOutputParser()).with_config(
        run_name="GenerateResponse"
    )
    
    # 결과 형식화 함수 (기존과 동일)
    def format_response(result):
        if isinstance(result, dict) and "docs" in result:
            # use scores already calculated by HybridRetriever
            scores = [doc.metadata.get("combined_score", 0.0) for doc in result.get("docs", [])]
            
            return {
                "answer": result.get("text", ""),
                "source_documents": result.get("docs", []),
                "similarity_scores": scores,
                "session_id": result.get("session_id", "default"),  # 세션 ID 보존
                "question": result.get("question", "")  # 원본 질문 보존
            }
        return result
    
    # 최종 체인 구성 - 원래 질문과 세션 ID 유지
    final_chain = (
        RunnablePassthrough.assign(
            chat_history=get_session_memory,
            # 다른 필드들은 그대로 유지
        )
        | context
        | RunnablePassthrough.assign(
            text=response_synthesizer
        )
        | RunnableLambda(format_response)
    )
    
    # 메모리 업데이트 함수 개선
    def update_memory_and_return(result):
        try:
            session_id = result.get("session_id", "default")
            
            if session_id in session_memories:
                # 질문과 답변 추출
                question = result.get("question", "")
                answer = result.get("answer", "")
                
                # 답변이 없는 경우 text 필드에서 가져옴
                if not answer and "text" in result:
                    answer = result["text"]
                
                # 메모리 업데이트
                if question and answer:
                    session_memories[session_id].save_context(
                        {"question": question},
                        {"answer": answer}
                    )
        except Exception as e:
            pass
            
        return result
    
    return RunnablePassthrough.assign(
        # 원본 입력 값 유지를 위한 패스스루 추가
        session_id=lambda x: x.get("session_id", "default"),
        question=lambda x: x.get("question", "")
    ) | final_chain | RunnableLambda(update_memory_and_return)


# Initialize LLM with settings from settings.py
llm = ChatOpenAI(
    model=settings.LLM_MODEL, 
    temperature=settings.LLM_TEMPERATURE, 
    streaming=settings.LLM_STREAMING
)

# Initialize retriever and answer chain
# These are the main components that will be used by the API
retriever = None
answer_chain = None

def initialize_chain():
    """Initialize retriever and answer chain if not already initialized."""
    # skip initialization when run_ingest command is executed
    if 'run_ingest' in sys.argv:
        print("run_ingest command is executed, skip initialization")
        return None
        
    global retriever, answer_chain
    if retriever is None or answer_chain is None:
        retriever = get_retriever()
        answer_chain = create_chain(llm, retriever)
    return answer_chain
