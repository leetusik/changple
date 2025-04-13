import json
import logging
import os
import uuid
from datetime import datetime, timedelta

from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from dotenv import load_dotenv
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import AIMessage, HumanMessage

from chatbot.models import ChatMessage, ChatSession

# Configure logging
logger = logging.getLogger(__name__)

# Import necessary components from chain service
# Make sure llm and get_retriever are accessible
try:
    from chatbot.services.chain import (
        create_chain,
        get_retriever,
        handle_post_generation,
        llm,
    )

    # Initialize retriever globally (assuming thread-safety)
    retriever = get_retriever()
    logger.info("Successfully imported chain components and initialized retriever.")
except ImportError as e:
    logger.critical(f"Failed to import chain components: {str(e)}")
    raise RuntimeError("챗봇 서비스 초기화 실패. 서버를 시작할 수 없습니다.")
except Exception as e:
    logger.critical(f"Failed to initialize retriever: {str(e)}")
    raise RuntimeError(
        "챗봇 서비스 초기화 실패 (Retriever). 서버를 시작할 수 없습니다."
    )

# load_dotenv()
load_dotenv()


def index(request):
    return render(request, "index.html")


class HomeView(View):
    """
    홈페이지 뷰
    사용자 인증 상태에 따라 동적으로 렌더링되는 단일 템플릿을 제공합니다.
    """

    def get(self, request):
        return render(request, "index.html")


def chat_view(request, session_nonce=None):
    # Handle POST request (creating a session with initial message)
    if request.method == "POST" and session_nonce is None:
        try:
            # Get message from form data
            initial_message = request.POST.get("message", "").strip()

            if not initial_message:
                return JsonResponse({"error": "Message is required"}, status=400)

            # Create a new chat session
            chat_session = ChatSession.objects.create(
                session_id=f"session_{uuid.uuid4().hex[:8]}",
                session_nonce=uuid.uuid4(),
                user=request.user if request.user.is_authenticated else None,
            )
            logger.info(f"Created chat session with ID: {chat_session.session_id}")

            # Save user message
            user_message = ChatMessage.objects.create(
                session=chat_session, role="user", content=initial_message
            )
            # Mark this session as having its initial message already saved
            chat_session.request_sent = True
            chat_session.save()

            # Return clean URL without query parameters, but add a new_chat=1 parameter
            # to indicate this is a newly created chat session and AI should respond right away
            redirect_url = f"{chat_session.get_absolute_url()}?new_chat=1"
            logger.info(f"Returning redirect URL: {redirect_url}")
            return JsonResponse({"redirect_url": redirect_url})
        except Exception as e:
            import traceback

            logger.error(f"CRITICAL ERROR in chat_view: {str(e)}")
            logger.error(traceback.format_exc())
            return JsonResponse(
                {
                    "error": f"Server error: {str(e)}",
                    "details": "Check server logs for details",
                },
                status=500,
            )

    # If no session_nonce is provided (URL path is just /chat/) and not a POST, create a new session
    if session_nonce is None:
        # Create a new chat session
        chat_session = ChatSession.objects.create(
            session_id=f"session_{uuid.uuid4().hex[:8]}",
            session_nonce=uuid.uuid4(),
            user=request.user if request.user.is_authenticated else None,
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

        # Format the chat history for JavaScript chain format
        chat_history_json = []
        i = 0
        messages_list = list(chat_messages.order_by("created_at"))
        while i < len(messages_list) - 1:
            if (
                messages_list[i].role == "user"
                and messages_list[i + 1].role == "assistant"
            ):
                chat_history_json.append(
                    {
                        "human": messages_list[i].content,
                        "ai": messages_list[i + 1].content,
                    }
                )
            i += 2

        # We're only checking for the existence of user messages, not returning the content
        # to avoid displaying it twice
        has_initial_message = chat_messages.filter(role="user").exists()
        initial_message = None

        # Check if this is likely a navigation from history
        is_from_history = False
        # First check if new_chat parameter exists - if so, this is a new chat, not from history
        if request.GET.get("new_chat") == "1":
            is_from_history = False
            logger.info("Detected new chat from URL parameter")
        # Otherwise check the referer
        elif request.META.get("HTTP_REFERER", ""):
            referer = request.META.get("HTTP_REFERER", "")
            logger.info(f"Request referer: {referer}")
            # If referer exists and contains index.html or the root path, it's likely coming from history
            if "index.html" in referer or referer.endswith("/"):
                is_from_history = True
                logger.info(f"Detected navigation from history: {referer}")

        # Only set initial_message if there's exactly one user message and not coming from history
        if chat_messages.count() == 1 and has_initial_message and not is_from_history:
            initial_message = chat_messages.filter(role="user").first().content
            logger.info(
                f"Setting initial message for auto-API call: {initial_message[:50]}..."
            )
        else:
            logger.info(
                f"Not setting initial message. Chat count: {chat_messages.count()}, Has initial: {has_initial_message}, From history: {is_from_history}"
            )

    except ChatSession.DoesNotExist:
        # Invalid nonce, create a new session
        chat_session = ChatSession.objects.create(
            session_id=f"session_{uuid.uuid4().hex[:8]}",
            session_nonce=uuid.uuid4(),
            user=request.user if request.user.is_authenticated else None,
        )
        # Redirect to the new session URL
        return redirect(chat_session.get_absolute_url())

    # Get user's remaining query count if user is authenticated
    remaining_queries = 0
    query_limit = 10  # Default limit
    is_premium = False

    if request.user.is_authenticated:
        # Check if user has available queries and get remaining count
        user = request.user

        # Reset counter if it's a new day
        if user.has_available_queries():
            remaining_queries = user.daily_query_limit - user.daily_queries_used

        query_limit = user.daily_query_limit
        is_premium = (
            user.is_premium
            and user.premium_until
            and user.premium_until > timezone.now()
        )

    context = {
        "chat_session": chat_session,
        "chat_history": chat_history,
        "chat_history_json": chat_history_json,
        "initial_message": initial_message,  # Pass initial message to template
        "remaining_queries": remaining_queries,
        "query_limit": query_limit,
        "is_premium": is_premium,
        "is_from_history": is_from_history,  # Pass this flag to template
    }

    return render(request, "index_chat.html", context)


@csrf_exempt
@require_POST
def chat(request):
    """챗봇 대화 API 엔드포인트 (스트리밍 방식)"""
    try:
        data = json.loads(request.body)
        query = data.get("query", "")
        session_nonce = data.get("session_nonce", "")

        # Clean up session_nonce if it contains query parameters
        if session_nonce and "?" in session_nonce:
            session_nonce = session_nonce.split("?")[0]

        # user query
        logger.info(f"User query (session: {session_nonce}): \n{query}")

        if not query:
            return JsonResponse({"error": "질문을 입력해주세요."}, status=400)

        # Check if user has available queries
        remaining_queries = 0
        query_limit = 10
        is_premium = False
        user = None

        if request.user.is_authenticated:
            user = request.user

            # Check if user has available queries
            if not user.has_available_queries():
                return JsonResponse(
                    {
                        "error": "일일 질문 한도에 도달했습니다. 내일 다시 시도하거나 프리미엄으로 업그레이드하세요.",
                        "remaining_queries": 0,
                        "query_limit": user.daily_query_limit,
                        "is_premium": user.is_premium,
                    },
                    status=403,
                )

            # Get remaining queries before incrementing
            remaining_queries = user.daily_query_limit - user.daily_queries_used
            query_limit = user.daily_query_limit
            is_premium = (
                user.is_premium
                and user.premium_until
                and user.premium_until > timezone.now()
            )

        # Get or create chat session
        try:
            chat_session = None
            if session_nonce:
                chat_session = ChatSession.objects.get(session_nonce=session_nonce)
            else:
                # If no nonce provided in API, it's likely an error or needs specific handling
                # For now, let's assume a nonce is required for the chat API
                return JsonResponse({"error": "Session nonce is required."}, status=400)

            # --- Load User Info from Django Session ---
            user_info = request.session.get(f"user_info_{session_nonce}", {})
            logger.info(f"Loaded user_info from session: {user_info}")
            # -----------------------------------------

            # --- Memory and Chain Creation per Request ---
            # 데이터베이스에서 대화 내역 가져오기
            messages = chat_session.messages.all().order_by("created_at")

            # Create a new memory buffer for this request
            memory = ConversationBufferMemory(
                return_messages=True,
                output_key="answer",
                input_key="question",
                memory_key="chat_history",
            )

            # Populate memory from DB messages
            for msg in messages:
                if msg.role == "user":
                    memory.chat_memory.add_user_message(msg.content)
                elif msg.role == "assistant":
                    memory.chat_memory.add_ai_message(msg.content)

            # Create the chain for this specific request, passing the populated memory
            request_chain = create_chain(llm=llm, retriever=retriever, memory=memory)
            # ----------------------------------------------

            # 세션 ID와 대화 기록을 포함한 체인 입력 구성
            chain_input = {
                "question": query,
                "user_info": user_info,
            }

            # Add authenticated user object to input if available (chain might use it)
            if user:
                chain_input["user"] = user

            # --- 스트리밍 응답 생성 ---
            def event_stream():
                full_answer = ""
                post_process_executed = False
                final_used_question = None

                try:
                    logger.info(f"Starting stream for session {session_nonce}")
                    stream = request_chain.stream(chain_input)

                    for chunk in stream:
                        full_answer += chunk
                        yield f"data: {json.dumps({'token': chunk})}\n\n"

                    logger.info(
                        f"Stream finished for session {session_nonce}. Full answer length: {len(full_answer)}"
                    )
                    post_processing_input = {
                        "question": chain_input.get("question"),
                        "user_info": chain_input.get("user_info"),
                    }
                    final_used_question = post_processing_input.get("question")

                    if final_used_question:
                        logger.info(
                            f"Executing post-generation for session {session_nonce}, Q: {final_used_question[:50]}..."
                        )
                        post_gen_result = handle_post_generation(
                            post_processing_input, full_answer, memory
                        )
                        updated_user_info = post_gen_result.get("updated_user_info")
                        post_process_executed = True

                        if updated_user_info is not None:
                            request.session[f"user_info_{session_nonce}"] = (
                                updated_user_info
                            )
                            logger.info(
                                f"Saved updated user_info to session {session_nonce}: {updated_user_info}"
                            )

                        if user and not is_premium:
                            user.increment_query_count()
                            logger.info(
                                f"Incremented query count for user {user.username}"
                            )

                        user_msg = ChatMessage.objects.create(
                            session=chat_session, role="user", content=query
                        )
                        ai_msg = ChatMessage.objects.create(
                            session=chat_session, role="assistant", content=full_answer
                        )
                        logger.info(
                            f"Saved user message (ID: {user_msg.id}) and AI message (ID: {ai_msg.id}) to DB for session {session_nonce}"
                        )

                    else:
                        logger.warning(
                            f"Skipping post-generation for session {session_nonce}: 'question' missing in prepared input."
                        )

                    yield f"data: {json.dumps({'end': True})}\n\n"

                except Exception as e:
                    logger.error(
                        f"Error during streaming or post-processing for session {session_nonce}: {e}",
                        exc_info=True,
                    )
                    yield f"data: {json.dumps({'error': '스트리밍 중 서버 오류가 발생했습니다.'})}\n\n"
                finally:
                    if not post_process_executed:
                        logger.warning(
                            f"Post-generation was not executed for session {session_nonce}."
                        )

            response = StreamingHttpResponse(
                event_stream(), content_type="text/event-stream"
            )
            response["Cache-Control"] = "no-cache"
            return response

        except ChatSession.DoesNotExist:
            return JsonResponse(
                {"error": "Invalid session nonce provided."}, status=404
            )
        except Exception as e:
            logger.error(f"Error in chat API (outer try-except): {e}", exc_info=True)
            return JsonResponse(
                {"error": "챗봇 API 처리 중 예기치 않은 오류가 발생했습니다."},
                status=500,
            )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error in chat API (outer try-except): {e}", exc_info=True)
        return JsonResponse(
            {"error": "챗봇 API 처리 중 예기치 않은 오류가 발생했습니다."}, status=500
        )
