import json
import logging
import os
import uuid
from datetime import datetime, timedelta

from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

# from django.utils.text import slugify
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from dotenv import load_dotenv
from langchain_core.documents import Document

# from langchain.memory import ConversationBufferMemory
from langchain_core.messages import AIMessageChunk
from langgraph.checkpoint.sqlite import SqliteSaver
from rest_framework.response import Response
from rest_framework.views import APIView

from chatbot.models import ChatMessage, ChatSession

# Configure logging
logger = logging.getLogger(__name__)

# Import necessary components from chain service
# Make sure llm and get_retriever are accessible
try:
    from chatbot.services.chain import get_graph
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

node_map = {
    "route_query": "질문 분류 중",
    "generate_queries": "관련 문서 찾는 중",
    "documents_handler": "적절한 문서 고르는 중",
}


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

        # Security check: Verify if the current user is the creator of the session or an admin
        if (
            chat_session.user
            and request.user != chat_session.user
            and not request.user.is_staff
        ):
            logger.warning(
                f"Unauthorized access attempt to session {session_nonce} by user {request.user.username if request.user.is_authenticated else 'anonymous'}"
            )
            # Return a 403 Forbidden response with our custom template
            return render(request, "403.html", status=403)

        # Get chat messages for this session
        chat_messages = chat_session.messages.all()

        # Format messages for template
        chat_history = []
        for message in chat_messages:
            message_data = {
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
                "id": message.id,  # Include message ID for all messages
            }
            # Include rating information for assistant messages
            if message.role == "assistant":
                message_data["good_or_bad"] = message.good_or_bad

            # assistant 메시지일 경우 helpful_documents 필드를 추가
            if message.role == "assistant" and message.helpful_documents:
                message_data["documents"] = message.helpful_documents
            else:
                message_data["documents"] = []
            chat_history.append(message_data)

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

        # # Clean up session_nonce if it contains query parameters
        # if session_nonce and "?" in session_nonce:
        #     session_nonce = session_nonce.split("?")[0]

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

                # Security check: Verify if the current user is the creator of the session or an admin
                if (
                    chat_session.user
                    and request.user != chat_session.user
                    and not request.user.is_staff
                ):
                    logger.warning(
                        f"Unauthorized API access attempt to session {session_nonce} by user {request.user.username if request.user.is_authenticated else 'anonymous'}"
                    )
                    return JsonResponse(
                        {
                            "error": "You do not have permission to access this chat session."
                        },
                        status=403,
                    )
            else:
                # If no nonce provided in API, it's likely an error or needs specific handling
                return JsonResponse({"error": "Session nonce is required."}, status=400)

            # --- Load User Info from Django Session ---
            user_info = request.session.get(f"user_info_{session_nonce}", {})
            logger.info(f"Loaded user_info from session: {user_info}")
            # -----------------------------------------

            # --- Memory and Chain Creation per Request ---
            # 데이터베이스에서 대화 내역 가져오기
            messages = chat_session.messages.all().order_by("created_at")

            # # Create a new memory buffer for this request
            # memory = ConversationBufferMemory(
            #     return_messages=True,
            #     output_key="answer",
            #     input_key="question",
            #     memory_key="chat_history",
            # )
            # messages_to_add = []
            # # Populate memory from DB messages
            # for i, msg in enumerate(messages):
            #     if msg.role == "user" and i != 0:
            #         # memory.chat_memory.add_user_message(msg.content)
            #         messages_to_add.append({"role": "user", "content": msg.content})
            #     elif msg.role == "assistant":
            #         # memory.chat_memory.add_ai_message(msg.content)
            #         messages_to_add.append(
            #             {"role": "assistant", "content": msg.content}
            #         )

            graph = get_graph()
            # ----------------------------------------------

            # --- 스트리밍 응답 생성 ---
            def event_stream():
                final_answer_streamed = ""  # Store the final answer as it's streamed
                last_yielded_token_data = None  # Keep track of the last thing we sent
                full_answer = ""

                try:
                    logger.info(f"Starting stream for session {session_nonce}")
                    # Set a timeout for stream operations
                    timeout = 120  # 2 minutes timeout
                    graph = get_graph()
                    with SqliteSaver.from_conn_string("checkpoints.sqlite") as memory:
                        graph = graph.compile(checkpointer=memory)
                        for chunk in graph.stream(
                            {"messages": [{"role": "user", "content": query}]},
                            config={
                                "configurable": {
                                    "thread_id": f"chat_{session_nonce}",
                                    "timeout": timeout,
                                }
                            },
                            stream_mode="messages",
                        ):
                            if (
                                isinstance(chunk, tuple)
                                and type(chunk[0]) == AIMessageChunk
                            ):
                                # Always log the node
                                current_node = node_map.get(
                                    chunk[1]["langgraph_node"], ""
                                )
                                # print(f"chunk: {current_node}")

                                # Always send node status update even if no content
                                # Send a node-only update if we haven't seen this node before
                                if (
                                    last_yielded_token_data is None
                                    or current_node
                                    != last_yielded_token_data.get("langgraph_node")
                                ):
                                    # Send a node-only update first
                                    node_data = {
                                        "langgraph_node": current_node,
                                    }
                                    yield f"data: {json.dumps(node_data)}\n\n"
                                    # print(f"Sent node-only update: {current_node}")

                                # Process content if available
                                answer_content = chunk[0].content
                                if (
                                    answer_content
                                    and answer_content != final_answer_streamed
                                ):
                                    final_answer_streamed = (
                                        answer_content  # Update the streamed answer
                                    )
                                    token_data = {
                                        "token": final_answer_streamed,
                                        "langgraph_node": current_node,
                                    }
                                    if token_data != last_yielded_token_data:
                                        yield f"data: {json.dumps(token_data)}\n\n"
                                        last_yielded_token_data = token_data
                                        full_answer += answer_content
                                        # Reduce logging frequency to save memory
                                        if len(full_answer) % 500 == 0:
                                            logger.debug(
                                                f"Sent answer chunk (current length: {len(full_answer)})"
                                            )
                        logger.info(
                            f"Stream finished for session {session_nonce}. Final answer length: {len(full_answer)}"
                        )

                        # --- Post-stream processing ---
                        post_processing_input = {
                            "question": query,  # Use original query
                        }
                        final_used_question = post_processing_input.get("question")

                        # Use the final_answer_streamed which contains the complete answer
                        if final_used_question and final_answer_streamed:
                            # Check if this is the initial message and if it was already saved
                            is_initial_message = (
                                chat_session.messages.count() == 1
                                and chat_session.request_sent
                            )

                            # Only save the user message if it's not the initial message that was already saved
                            if not is_initial_message:
                                user_msg = ChatMessage.objects.create(
                                    session=chat_session, role="user", content=query
                                )
                                logger.info(
                                    f"Saved user message (ID: {user_msg.id}) to DB for session {session_nonce}"
                                )
                            else:
                                logger.info(
                                    f"Skipping saving duplicate user message for session {session_nonce}"
                                )

                            # --- Extract data from final state BEFORE saving AI message ---
                            doc_info = []
                            retrieved_queries = []  # Initialize retrieve_queries list
                            try:
                                # Get state from the graph
                                state = graph.get_state(
                                    config={
                                        "configurable": {
                                            "thread_id": f"chat_{session_nonce}"
                                        }
                                    }
                                )
                                logger.info(
                                    f"State type: {type(state)}"
                                )  # Log state type for debugging

                                # --- Extract Documents (doc_info) ---
                                docs = []
                                if hasattr(state, "documents"):
                                    docs = state.documents
                                elif hasattr(state, "values") and hasattr(
                                    state.values, "get"
                                ):
                                    docs = state.values.get("documents", [])
                                elif isinstance(state, dict):
                                    docs = state.get("documents", [])

                                if docs and hasattr(docs, "__iter__"):
                                    for doc in docs:
                                        if hasattr(doc, "metadata"):
                                            doc_info.append(
                                                {
                                                    "title": doc.metadata.get(
                                                        "title", "No title"
                                                    ),
                                                    "source": doc.metadata.get(
                                                        "source", "No source"
                                                    ),
                                                }
                                            )
                                    logger.info(
                                        f"Extracted {len(doc_info)} document(s) for helpful_documents"
                                    )

                                # --- Extract Retrieve Queries ---
                                if hasattr(state, "values") and hasattr(
                                    state.values, "get"
                                ):
                                    retrieved_queries = state.values.get(
                                        "retrieve_queries", []
                                    )
                                elif isinstance(state, dict):
                                    retrieved_queries = state.get(
                                        "retrieve_queries", []
                                    )

                                if retrieved_queries:
                                    logger.info(
                                        f"Extracted {len(retrieved_queries)} retrieve queries"
                                    )
                                else:
                                    logger.info("No retrieve queries found in state")

                            except Exception as e:
                                logger.error(
                                    f"Error extracting document or query info from state: {e}",
                                    exc_info=True,
                                )
                            # --- End extraction ---

                            # Always save the AI response, now including the extracted fields
                            ai_msg = ChatMessage.objects.create(
                                session=chat_session,
                                role="assistant",
                                content=full_answer,
                                retrieve_queries=(
                                    retrieved_queries if retrieved_queries else None
                                ),  # 저장할 쿼리가 있으면 저장, 없으면 null
                                helpful_documents=(
                                    doc_info if doc_info else None
                                ),  # 저장할 문서 정보가 있으면 저장, 없으면 null
                            )
                            logger.info(
                                f"Saved AI message (ID: {ai_msg.id}) with retrieve_queries and helpful_documents to DB for session {session_nonce}"
                            )

                            # Send message_pk to frontend for rating functionality
                            yield f"data: {json.dumps({'message_pk': ai_msg.id})}\n\n"

                            # Send end signal with message_pk included
                            yield f"data: {json.dumps({'end': True, 'documents': doc_info or [], 'message_pk': ai_msg.id, 'remaining_queries': remaining_queries, 'query_limit': query_limit, 'is_premium': is_premium})}\n\n"
                            return
                        elif not full_answer:
                            logger.warning(
                                f"Skipping DB saving for session {session_nonce} as no answer was generated/streamed (final_answer_streamed empty)."
                            )
                            # End signal without message_pk since no message was saved
                            yield f"data: {json.dumps({'end': True, 'remaining_queries': remaining_queries, 'query_limit': query_limit, 'is_premium': is_premium})}\n\n"
                            return
                        else:
                            logger.warning(
                                f"Skipping post-generation DB saving for session {session_nonce}: 'question' missing."
                            )
                            # End signal without message_pk
                            yield f"data: {json.dumps({'end': True, 'remaining_queries': remaining_queries, 'query_limit': query_limit, 'is_premium': is_premium})}\n\n"
                            return

                except Exception as e:
                    logger.error(
                        f"Error during streaming or post-processing for session {session_nonce}: {e}",
                        exc_info=True,
                    )
                    # Avoid sending 'end' signal again if an error occurred before it was sent
                    try:
                        yield f"data: {json.dumps({'error': '스트리밍 중 서버 오류가 발생했습니다.'})}\n\n"
                    except Exception as yield_err:
                        logger.error(f"Error yielding error message: {yield_err}")

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


def privacy_policy(request):
    """개인정보처리방침 페이지"""
    return render(request, "privacy_policy.html")


class Rating(APIView):
    def post(self, request):
        # Change this line:
        # data = json.loads(request.body)

        # To this:
        data = request.data

        message_pk = data.get("message_pk")
        rating = data.get("rating")

        try:
            message = ChatMessage.objects.get(pk=message_pk)
        except ChatMessage.DoesNotExist:
            return JsonResponse({"error": "Message not found"}, status=404)

        if message.role != "assistant":
            return JsonResponse(
                {"error": "Only assistant messages can be rated"}, status=400
            )

        if rating == None:
            message.good_or_bad = None
        else:
            message.good_or_bad = rating
        message.save(update_fields=["good_or_bad"])

        return JsonResponse(
            {"status": "success", "message_pk": message_pk, "rating": rating}
        )
