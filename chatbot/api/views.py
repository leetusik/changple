import logging
import os
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.text import slugify
from django.views import View
from dotenv import load_dotenv
from rest_framework.decorators import api_view
from rest_framework.response import Response

from chatbot.models import ChatMessage, ChatSession

# Configure logging
logger = logging.getLogger(__name__)

# Try to import answer_chain, handle import errors gracefully
try:
    from chatbot.services.chain import answer_chain

    logger.info("Successfully imported answer_chain")
except ImportError as e:
    logger.error(f"Failed to import answer_chain: {str(e)}")

    # Create a dummy function that will be used if the real one is not available
    def dummy_answer_chain():
        def invoke(input_data):
            logger.warning(
                "Using dummy answer_chain because the real one couldn't be imported"
            )
            return "죄송합니다. 현재 AI 서비스를 사용할 수 없습니다. 나중에 다시 시도해주세요."

        return type("DummyChain", (), {"invoke": staticmethod(invoke)})()

    answer_chain = dummy_answer_chain()

# 파일 시작 부분에 .env 로드
load_dotenv()

# Create your views here.


def index(request):
    # 메인 페이지 렌더링
    return render(request, "index.html")


def chat_no_nonce_view(request):
    # Handle POST request (creating a session with initial message)
    if request.method == "POST":
        try:
            # Log request details for debugging
            logger.info(f"Received POST to chat_no_nonce_view")
            logger.info(f"Content type: {request.content_type}")
            logger.info(f"POST data keys: {list(request.POST.keys())}")

            # Get message from form data
            initial_message = request.POST.get("message", "").strip()
            logger.info(f"Extracted message: '{initial_message}'")

            if not initial_message:
                logger.warning("Empty message received")
                return JsonResponse({"error": "Message is required"}, status=400)

            # Create a new chat session
            chat_session = ChatSession.objects.create(
                session_id=f"session_{uuid.uuid4().hex[:8]}",
                session_nonce=uuid.uuid4(),
            )
            logger.info(f"Created chat session with ID: {chat_session.session_id}")

            # Save user message
            user_message = ChatMessage.objects.create(
                session=chat_session, role="user", content=initial_message
            )
            logger.info(f"Saved user message (ID: {user_message.id}) to database")

            # Return clean URL without query parameters
            redirect_url = chat_session.get_absolute_url()
            logger.info(f"Returning redirect URL: {redirect_url}")
            return JsonResponse({"redirect_url": redirect_url})

        except Exception as e:
            import traceback

            logger.error(f"CRITICAL ERROR in chat_no_nonce_view: {str(e)}")
            logger.error(traceback.format_exc())
            return JsonResponse(
                {
                    "error": f"Server error: {str(e)}",
                    "details": "Check server logs for details",
                },
                status=500,
            )

    # Handle GET request (regular redirect)
    return chat_view(request, None)


def chat_view(request, session_nonce=None):
    # If no session_nonce is provided (URL path is just /chat/), create a new session
    if session_nonce is None:
        # Create a new chat session
        chat_session = ChatSession.objects.create(
            session_id=f"session_{uuid.uuid4().hex[:8]}", session_nonce=uuid.uuid4()
        )
        # Redirect to the new session URL with the nonce in the path
        return redirect(chat_session.get_absolute_url())

    # Get chat session from database using the nonce from URL path
    try:
        chat_session = ChatSession.objects.get(session_nonce=session_nonce)
        # Get chat messages for this session
        chat_messages = chat_session.messages.all()

        # Format messages for template
        chat_history = [
            {
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in chat_messages
        ]

        # Check if there's an initial message already in the database
        initial_message = None
        if chat_messages.filter(role="user").exists():
            initial_message = chat_messages.filter(role="user").first().content

    except ChatSession.DoesNotExist:
        # Invalid nonce, create a new session
        chat_session = ChatSession.objects.create(
            session_id=f"session_{uuid.uuid4().hex[:8]}", session_nonce=uuid.uuid4()
        )
        # Redirect to the new session URL
        return redirect(chat_session.get_absolute_url())

    # 템플릿에 전달할 기본 컨텍스트
    context = {
        "chat_session": chat_session,
        "chat_history": chat_history,
        "initial_message": initial_message,  # Pass initial message to template
    }

    # index_chat.html 템플릿 렌더링
    return render(request, "index_chat.html", context)


class HomeView(View):
    """
    홈페이지 뷰
    사용자 인증 상태에 따라 동적으로 렌더링되는 단일 템플릿을 제공합니다.
    """

    def get(self, request):
        # 통합된 템플릿 사용 - 템플릿 내에서 인증 상태에 따라 조건부 렌더링
        return render(request, "index.html")


@api_view(["POST"])
def chat(request):
    """챗봇 대화 API 엔드포인트"""
    data = request.data
    query = data.get("query", "")
    session_nonce = data.get("session_nonce", "")
    client_history = data.get("history", [])

    if not query:
        return Response({"error": "질문을 입력해주세요."}, status=400)

    # Get or create chat session
    try:
        chat_session = None
        if session_nonce:
            chat_session = ChatSession.objects.get(session_nonce=session_nonce)
        else:
            chat_session = ChatSession.objects.create(
                session_id=f"session_{uuid.uuid4().hex[:8]}", session_nonce=uuid.uuid4()
            )

        # Log the input
        logger.info(f"Received question: {query}")
        if client_history:
            logger.info(f"With client history of {len(client_history)} entries")

        # Convert database history to the format expected by chain.py
        chain_history = []

        # If client sent history, use that instead of rebuilding from database
        # This ensures follow-up question handling works properly with recent context
        if client_history:
            chain_history = client_history
        else:
            # If no client history, build from database
            messages = chat_session.messages.all().order_by("created_at")
            i = 0
            while i < len(messages) - 1:
                if messages[i].role == "user" and messages[i + 1].role == "assistant":
                    chain_history.append(
                        {"human": messages[i].content, "ai": messages[i + 1].content}
                    )
                i += 2

        # Prepare input for the chain
        chain_input = {"question": query, "chat_history": chain_history}

        # Log what's being sent to the chain
        logger.info(
            f"Chain input: question={query}, history_length={len(chain_history)}"
        )

        # Run the chain and get the response
        chain_response = answer_chain.invoke(chain_input)

        # Extract response text and relevance scores
        if isinstance(chain_response, dict):
            response = chain_response.get("answer", chain_response)
            source_docs = chain_response.get("source_documents", [])
            
            # similarity scores가 있는 경우 추출
            if hasattr(chain_response, "similarity_scores"):
                search_results = []
                for doc, score in zip(source_docs, chain_response.similarity_scores):
                    search_results.append({
                        "metadata": {
                            "title": doc.metadata.get("title", f"Source {i+1}"),
                            "url": doc.metadata.get("url", ""),
                            "similarity_score": f"{score:.2f}"  # 유사도 점수 추가
                        },
                        "content": doc.page_content[:200]
                    })
            else:
                # Extract search results if they exist in the response
                search_results = chain_response.get("search_results", [])
                # Extract source documents if they exist
                source_docs = chain_response.get("source_documents", [])
        else:
            response = chain_response
            search_results = []
            source_docs = []

        # If source_docs is available but search_results is not, convert source_docs to search_results format
        if not search_results and source_docs:
            search_results = []
            for i, doc in enumerate(source_docs):
                search_results.append(
                    {
                        "metadata": {
                            "title": doc.metadata.get("title", f"Source {i+1}"),
                            "url": doc.metadata.get("url", ""),
                        },
                        "content": doc.page_content[:200],  # Limit content length
                    }
                )

        # If chain.py's retriever_chain was used, try to extract the docs that were retrieved
        if not search_results:
            try:
                # Get the docs from context
                docs = chain_input.get("docs", [])
                if docs:
                    search_results = []
                    for i, doc in enumerate(docs):
                        search_results.append(
                            {
                                "metadata": {
                                    "title": doc.metadata.get("title", f"Source {i+1}"),
                                    "url": doc.metadata.get("url", ""),
                                },
                                "content": doc.page_content[
                                    :200
                                ],  # Limit content length
                            }
                        )
            except Exception as e:
                logger.info(f"Could not extract docs from context: {str(e)}")

        # Save the messages to the database
        ChatMessage.objects.create(session=chat_session, role="user", content=query)
        ChatMessage.objects.create(
            session=chat_session, role="assistant", content=response
        )

        # Update chain history with this interaction
        updated_history = list(chain_history)  # Make a copy
        updated_history.append({"human": query, "ai": response})

        return Response(
            {
                "response": response,
                "search_results": search_results,
                "history": updated_history,
                "session_nonce": str(chat_session.session_nonce),
            }
        )

    except Exception as e:
        logger.error(f"Error in chat API: {str(e)}")
        print(f"Error in chat API: {str(e)}")
        return Response({"error": str(e)}, status=500)
