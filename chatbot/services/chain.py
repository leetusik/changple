import logging
import os
import sys
from operator import itemgetter
from typing import Dict, List, Optional, Sequence, Any, AsyncIterator, Iterator

from django.db import models
from langchain.memory import ConversationBufferMemory
from langchain_community.vectorstores import Pinecone as LangchainPinecone
from langchain_core.documents import Document
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import AIMessageChunk
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import (
    Runnable,
    RunnableBranch,
    RunnableLambda,
    RunnablePassthrough,
    RunnableConfig,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from pinecone import Pinecone
from pydantic import BaseModel

from chatbot.services.ingest import get_embeddings_model
from scraper.models import NaverCafeData
from users.models import User

# Template for rephrasing follow-up questions based on chat history
REPHRASE_TEMPLATE = """\
다음 대화와 후속 질문을 바탕으로, 후속 질문을 독립적인 질문으로 바꾸세요.

대화 기록: 
{chat_history}

<독립 질문 생성 가이드>
1. 후속 질문에서 크게 변형하거나 왜곡하지 마세요.
2. 대화 기록을 통해 전체적인 문맥을 파악하세요.
3. 단 하나의 독립 질문을 생성하세요.
4. 충분히 이해가능한 수준으로 판단된다면, 바꾸지 마세요.
5. 창플에 관한 질문이라면, 앞에 [창플] 이라고 붙이세요.
6. 후속 질문에서 등장하는 단어를 모두 사용하세요.
</독립 질문 생성 가이드>

후속 질문: {question}
독립적인 질문:"""
CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(REPHRASE_TEMPLATE)

CATEGORIES = [
    "창플의 구체적 조언",
    "창플의 질문과 조언",
    "창플의 업계 일반적 질문 대답",
    "창플과 관련된 질문 대답",
]

# Define the example Q&A for each category
EXAMPLE_QA_MAP = {
    "창플의 구체적 조언": """
q. 30대 초반 남성인데, 분식집을 창업하려고 합니다. 자본금은 5천만원 정도 있고, 프랜차이즈로 시작하려고 하는데 어떤 점을 고려해야 할까요? 아이는 없고 사업에 온전히 시간을 할애할 수 있습니다.

a. 분식집창업은 대표적인 상권입지가 중요한 업종입니다. 특별히 찾아가서 먹는 것이 아니라, 내가 다니는 입지에 눈으로 발로 걸치면 그곳에가서 부담없이 사먹는것이죠.. 분식뿐만 아니고 대부분의 부담없이 즐기는 저가커피,빵집,와플가게나 핫도그집들도 다 비슷하게 평수가 작아서 시설비는 적게 드는것처럼 보이지만, 사실 그 업종들은 점포구입비용(보증금+권리금)을 많이 써야 하는 업종들입니다. 지금 그런 업종으로 망하는 초보창업자들이 언제나 실패하는건 점포비용으로는 권리금도 없는 곳에 들어가고 프랜차이즈에서 자신들의 컨셉이라고 불리는 인테리어비용을 들여서 하다보니, 망하는것이죠.. 좋은 자리에 있어야 하는 업종인데 시설비용때문에 나쁜자리에 들어가는것이죠.. 창업자금 5천만원이면 프랜차이즈본사 인테리어비용에도 못미치는 비용입니다. 프랜차이즈를 하게 되면 결국 배달프랜차이즈를 하게 되는데 문제는 배달프랜차이즈는 사실상 물류공급유통회사이기 때문에 그에 맞게 원가율이 높아집니다. 원가율이 높아져서 35% 40%가 되면 배달관련비용 30%가 합해지게 되어 결국 남은 30%로 임대료내고 인건비주고 나면 사실상 남는게 없는 프랜차이즈의 노예가 될 가능성이 높습니다.

만약에 5천만원밖에 없다면, 동네상권에서 망한 식당을 보증금2천만원 권리금1천만원 총 3천만원짜리 식당을 인수해서, 안주를 떡볶이와 튀김류들을 같이 만들어내서 안주로서의 분식으로 접근하는것이 좋습니다. 창플에서 만든 브랜드인 레이디오분식과 크런디라는 브랜드를 참조해도 좋고, 망원동튀맥이라고 하는 매장의 모습도 참고하면 좋습니다. 분식을 빙자한 술집으로 하게 되면 어느동네던지 기본 테이블단가가 나오면서 사람을 덜쓰고도 생존할수 있습니다. 분식은 원가가 낮고 미리 끓여놓고 튀겨놓으면 사람인건비도 많이 안써도 되기 때문입니다. 아이가 없으시면 더더욱 저녁과 밤을 겸해서 다른 분식집들이 문닫을때 장사하면 오히려 경쟁자들이 없어서 더 잘될수도 있습니다.
""",
    "창플의 질문과 조언": """
q. 돈까스집 창업을 생각 중인데 어떻게 시작해야 할까요?

a. 일반적으로 부담없이 먹거나 배달시켜먹는 저렴한 돈가스집을 이야기하는것인가요? 아니면 차타고 와서 먹고 가는 경양식집돈가스를 얘기하는건가요? 아니면 외식성격으로 찾아와서 먹는 일본식 두꺼운 돈가스집을 이야기하시는 건가요?

일반적으로 같은 돈가스집이라고해도 부담없이 먹는 돈가스는 상권입지가 중요합니다. 가성비가 좋아야 하고 남녀노소 만족스러워야 하기 때문에 대중적인 맛을 유지를 잘해야 합니다. 상권입지가 좋으려면 점포구입비용에 더 투자를 해야 합니다 보증금과 권리금을 합한 금액이 최소 1억정도는 되어야 합니다. 그렇게 안되면 매출이 꾸준하지 않고 많이 나오는날은 많이 나오고 안나오는 날은 안나오는 편차가 있는 매출이 나게 됩니다. 그렇게 되면 고정비는 그대로인데 매출이 편차가 나면 문제가 생기죠.. 그렇게 입지가 안좋으면 결국 배달에 의존하게 되고, 배달에 의존하게 되면 30%의 수수료를 또 감당해야 하는데 그렇게 되면 매출은 나오는데 안남게 되는 상황도 발생합니다. 그래서 부담없이 먹는 돈가스집을 하려면 최소 2억이상의 투자금을 준비하셔야 합니다.

찾아오는 스타일의 우리집만의 외식형 돈가스집이라면 오히려 단가도 더 올려도 되고 찾아오기 때문에 입지가 꼭 좋지 않아도 됩니다. 

다만, 사람들이 몰리는 집객상권에는 있어야 합니다. 동네상권으로는 사람들이 안찾아오니.. 각 지역별 사람들이 모이는 곳에 들어가되 좋은입지에 들어가지 말고 온라인입지를 키워서 그곳으로 오게 하는 전략이 필요합니다.

돈가스클럽처럼 경양식돈가스같은 경우는, 해장국이나 설렁탕 입지에 들어가야 합니다. 차로 이동하면서 먹는 고객들을 대상으로 하기 때문에 주차와 평수에도 신경을 써야 합니다. 

결론적으로 같은 돈가스집이라고 해도, 창업비용이 작으면 가성비로 남녀노소 다 좋아하는 돈가스집을 하면 안됩니다. 오히려 돈가스의 퀄리티와 주류를 동반한 머무를수 있는 요소를 가지고 공간기획까지 들어가서 오고싶은곳을 만드는것이 가장 안전한 방법입니다.

항상 초보들은 본인들이 초보이기 때문에 가성비 부담없는 음식을 하려 하지만, 가성비에 부담없는 음식을 파는 평식업은 대기업과 큰 프랜차이즈들의 영역입니다. 우린 틈새로 가야 내가 가진 작은 창업비용으로 생존할수 있습니다.
""",
    "창플의 업계 일반적 질문 대답": """
q. 요즘 트렌드인 식당 업종은 무엇인가요?

a. 창플에서는 트랜드를 말하지 않습니다. 트렌드는 그 트렌드를 이용해서 수익을 창출하려는 사업가들의 상술에 불과합니다. 트렌드보다는 방향성에 주목합니다. 

가령 지금은 아주 초가성비로 가던지, 아니면 확실하게 소비를 자랑할수 있는곳으로 가던가 소비의 방향이 확실합니다.

그러면 초가성비로 트랜드를 이끄는 브랜드가 있을것이고, 소비를 자랑할수 있는 그런 브랜딩을 통해서 이끄는 브랜드가 있을것이고, 기타 다른 브랜드들이 있을겁니다.

초보창업자들은 그 방향성에 대한 생각을 안하고 그런 방향성에 부합하는 브랜드를 보고 그대로 따라가는 경향이 있습니다 그렇게 트랜드라는 이유로 그 브랜드자체를 따라가면 순식간에 컨텐츠소비가 끝나면서 공멸하는 경우들이 많습니다. 앞서 이야기한 칼럼들을 살펴보시고, 현재 시장의 모습과 전망을 알아가시길 바랍니다.
""",
    "창플과 관련된 질문 대답": """
q. 창플은 어떤 일을 하는 회사인가요?

a. 창플은 초보창업자들의 생존을 위해 존재하는 회사입니다. 생존포인트를 연구하고, 그에 따른 브랜드를 만들고(아키프로젝트) 또한 그렇게 만든 브랜드를 또다른 초보창업자들이 할수 있게(팀비즈니스)전수창업식의 창업도 추천하고 있습니다.

창플의 생존방식은 명확합니다. 창플의 생존공식이 담긴 파전에 막걸리집이론을 참조하시면 알겠지만, 중간유통거품없이 원재료를 받아서 원가를 낮추고, 인테리어같은 값비싼 비용을 들이지 않고 실제 고객들에게 임팩트를 주는 vmd작업을 통해서 시설비용을 아끼고. 사장 본인의 몸을 갈아넣어서 직원및 알바1명으로 같이 창업을 하면 결코 망하지 않는다는 것이죠

브랜드나 아이템 업종이 문제가 아니라, 밥집을 하던지 술집을 하던지 고깃집을 하던지 그 어떤 업을 하던지 장사구조를 그렇게 잡고 자신이 감당할수 있는 범위의 창업비용을 가지고, 내몸을 이용해서 생존할수 있게 해야 한다는것입니다.

그에 대한 사례가 창플카페에는 무수히 많습니다. 매출은 적어도 결코 죽지 않는다는 사례를 보여주며, 초보들의 첫창업을 망하지 않게 돕는 그런 회사입니다.
""",
}

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.8,
    max_tokens=4000,
)

retriever = None

logger = logging.getLogger(__name__)


def get_post_content(post_id: int) -> str:
    """Retrieve original post content from NaverCafeData using post_id"""
    try:
        post = NaverCafeData.objects.get(post_id=post_id)
        # return f"Title: {post.title}\n\nContent: {post.content}"
        return f"{post.content}"
    except NaverCafeData.DoesNotExist:
        return "Post content not found."


def get_retriever() -> BaseRetriever:
    """Initialize and return the Pinecone retriever"""
    api_key = os.environ.get("PINECONE_API_KEY")
    environment = os.environ.get("PINECONE_ENVIRONMENT")
    index_name = os.environ.get("PINECONE_INDEX_NAME")

    pc = Pinecone(api_key=api_key, environment=environment)
    index = pc.Index(index_name)

    embeddings = get_embeddings_model()

    vectorstore = LangchainPinecone(index, embeddings, "text")

    return vectorstore.as_retriever(
        search_kwargs={
            "k": 10,
            "filter": {},  # Will be updated dynamically based on category
            # "score_threshold": 0.7,
        }
    )


def determine_category(question: str, user_info: Dict) -> str:
    """Determine the category of the question based on user info and question content"""
    # Create a context with user information and question
    context = f"유저 정보: {user_info}\n\n유저 질문: {question}"

    # Use LLM to determine the category
    category_prompt = ChatPromptTemplate.from_template(
        """
    유저 질문과 유저 정보를 바탕으로 질문의 카테고리를 결정하세요.
    
    {context}
    
    각 카테고리 별 질문 예시:
    
    1. 창플의 구체적 조언:(하고싶은 업종, 그리고 숫자가 질문에 포함되어 있는 경우)
    "30대 초반 남성인데, 분식집을 창업하려고 합니다. 자본금은 5천만원 정도 있고, 프랜차이즈로 시작하려고 하는데 어떤 점을 고려해야 할까요? 아이는 없고 사업에 온전히 시간을 할애할 수 있습니다."
    
    2. 창플의 질문과 조언:(하고싶은 업종이나 브랜드가 질문에 포함되어 있는 경우)
    "돈까스집 창업을 생각 중인데 어떻게 시작해야 할까요?"
    
    3. 창플의 업계 일반적 질문 대답:(창플과 직접적인 관련이 없는 업계 트렌드를 질문하는 경우)
    "요즘 트렌드인 식당 업종은 무엇인가요?"
    
    4. 창플과 관련된 질문 대답:(창플과 직접적인 관련이 있는 질문을 하는 경우)
    "창플은 어떤 일을 하는 회사인가요?"
    
    아래의 카테고리 중 하나를 선택하세요:
    - 창플의 구체적 조언
    - 창플의 질문과 조언
    - 창플의 업계 일반적 질문 대답
    - 창플과 관련된 질문 대답
    
    If none of the above categories fit, respond with "unknown".
    
    Category:
    """
    )

    category_chain = category_prompt | llm | StrOutputParser()
    result = category_chain.invoke({"context": context})

    # Clean up the response
    for category in CATEGORIES:
        if category in result:
            return category

    return "unknown"


def update_user_information(user_info: Dict, question: str) -> Dict:
    """Update user information based on question content"""

    update_prompt = ChatPromptTemplate.from_template(
        """
    주어진 유저의 질문을 바탕으로, 업데이트 할 수 있는 정보를 추출하세요.

    현재 유저 정보:
    {user_info}
    
    유저의 질문:
    {question}
    
    유저 정보 항목:
    - 나이
    - 성별
    - 경력
    - 창업 경험 여부
    - 관심 업종
    - 관심 업종의 구체적 방향성
    - 창업 목표
    - 채팅 목적
    - 수익 목표
    - 창업 예산
    - 창업 예산 중 대출금 비중
    - 돌봐야하는 가족 구성원 여부
    - 관심 특정 브랜드 여부
    - 관심 특정 브랜드 종목
    - 기타 특이사항
    
    각 항목에 대해, 새로운 정보가 있으면 추가하세요. 그렇지 않으면 해당 항목을 그대로 두세요. 모순되는 정보가 있으면 최신화 하세요.
    
    YOUR RESPONSE MUST BE VALID JSON, nothing else, no explanations.

    예시:
    {{
        "나이": "35세",
        "성별": "남성",
        "경력": "10년 IT 경력",
        "창업 경험 여부": "있음",
        "관심 업종": "치킨",
        "관심 업종의 구체적 방향성": "동네에서 편하게 들를 수 있는 맥주 + 치킨집을 창업하려고 함. 치킨집 주변에 주차공간이 있으면 좋겠음.",
        "창업 목표": "밤에는 장사하고, 낮에는 좀 쉴 수 있도록 워라밸을 지킬 수 있는 사업이 하고싶음.",
        "채팅 목적": "치킨집 인테리어 조언을 듣기",
        "수익 목표": "월 순수익 300만원",
        "창업 예산": "5000만원",
        "창업 예산 중 대출금 비중": "30%",
        "돌봐야하는 가족 구성원 여부": "없음",
        "관심 특정 브랜드 여부": "있음",
        "관심 특정 브랜드 종목": "네네치킨, 호식이두마리치킨",
        "기타 특이사항": "소심한 성격, 인상이 별로 안좋음, 치킨을 하루에 하나씩 먹음",
        ...
    }}
    """
    )

    update_chain = update_prompt | llm | StrOutputParser()
    result = update_chain.invoke({"user_info": user_info, "question": question})

    try:
        import json

        # Check if we received a proper response
        if not result or result.strip() == "":
            logger.warning("Empty result received from LLM")
            return user_info

        # Try to clean up the result by removing any non-JSON content
        result = result.strip()
        # If it starts with a backtick code block, clean it
        if result.startswith("```json"):
            result = result.split("```json")[1]
            if "```" in result:
                result = result.split("```")[0]
        elif result.startswith("```"):
            result = result.split("```")[1]
            if "```" in result:
                result = result.split("```")[0]

        result = result.strip()
        logger.info(f"Cleaned result: {result}")

        updated_info = json.loads(result)
        logger.info(f"Parsed JSON: {updated_info}")

        # Create a new dict to avoid reference problems
        final_info = {}

        # Start with all existing user_info values
        for key, value in user_info.items():
            final_info[key] = value

        # Update with values from updated_info where they exist and aren't empty
        for key, value in updated_info.items():
            if value:  # Only update if value is not empty/None
                final_info[key] = value
                logger.info(f"Updated field {key} with value: {value}")

        # Compare the original and final dicts to see if anything changed
        if final_info != user_info:
            logger.info(f"Information updated from {user_info} to {final_info}")
        else:
            logger.info("No changes detected in user information")

        return final_info
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        logger.error(f"Failed to parse result as JSON: {result}")
        return user_info
    except Exception as e:
        logger.error(f"Error updating user information: {e}", exc_info=True)
        return user_info


def create_specific_advice_chain() -> Runnable:
    """Create a chain for specific entrepreneurship advice questions"""
    prompt = ChatPromptTemplate.from_template(
        """
    당신은 요식업 컨설팅, 브랜딩 전문 회사 창플의 대표 한범구의 AI Clone입니다.
  
    당신은 상세하고, 실행가능한 조언을 합니다. 당신의 대답은 구체적인 숫자, 계산(필요시), 그리고 실용적인 단계를 제공해야합니다.
  
    사용자 정보:
    {user_info}
     
    관련 에세이 (주요 답변 근거):
    {primary_context}
    
    창플 철학 참고 자료:
    {philosophy_context}
      
    예시 질문과 대답:
    {example}

    대화 기록: q. 
    {chat_history}
 
    관련 에세이, 창플 철학 참고 자료, 예시 질문과 대답을 활용하여 사용자 질문에 답하세요.
    <답변 가이드>
    1. 질문의 핵심에 대해 답하세요.
    2. 질문에 대해 구체적이고 실행 가능한 조언을 하세요.
    3. 구체적인 숫자, 계산(필요시)을 적극적으로 활용하세요.
    4. 창플의 비즈니스 로직을 적극 활용하세요.
    5. 상대방이 직면할 수 있는 문제를 제시하고, 다른 접근 방법에 대해 설명하세요.
    6. 현실적으로 기대할 수 있는 수익, 성공 가능성 등을 제시하세요.
    7. 400 단어를 사용해서 답변하세요.
    8. 말을 반복하지 마세요.
    9. 주어진 관련 에세이의 문체, 어투를 따라하세요.
    10. 비유적 표현을 활용하세요.
    11. 말을 반복하지 마세요.
    12. 대화기록이 있다면, 활용해서 어색하지 않은 대답을 하세요.
    </답변 가이드>

    사용자 질문:
    {question}

    답변:
    """
    )

    return prompt | llm | StrOutputParser()


def create_question_advice_chain() -> Runnable:
    """Create a chain for questions seeking advice"""
    prompt = ChatPromptTemplate.from_template(
        """
    당신은 요식업 컨설팅, 브랜딩 전문 회사 창플의 대표 한범구의 AI Clone입니다.
  
    상대의 질문을 명확하게 하는 질문으로 시작하세요. 그리고 다양한 선택지들을 제시하며 다양한 관점과 비즈니스 모델을 소개하세요.
  
    사용자 정보:
    {user_info}
     
    관련 에세이 (주요 답변 근거):
    {primary_context}
    
    창플 철학 참고 자료:
    {philosophy_context}
      
    예시 질문과 대답:
    {example}

    대화 기록:
    {chat_history}
 
    관련 에세이, 창플 철학 참고 자료, 예시 질문과 대답을 활용하여 사용자 질문에 답하세요.
    <답변 가이드>
    1. 상대의 질문을 구체화 하는 질문으로 시작하세요.
    2. 구체적 조언을 해주기 위해 상대방의 창업 예산, 나이, 창업 경험 등을 물어보세요.
    2. 질문에서 구체적으로 발전할 수 있는 비즈니스의 형태 들을 소개하세요.
    3. 주어진 관련 에세이의 문체, 어투를 따라하세요.
    4. 400 단어를 사용해서 답변하세요.
    5. 다양한 비즈니스 모델과 접근 방법을 소개하세요.
    6. 창플의 비즈니스 로직을 적극 활용하세요.
    7. 여러 상황에 맞는 조건부 조언을 하세요.
    8. 유저 정보에 대해서 직접적으로 언급하지 마세요.
    9. 비유적 표현을 활용하세요.
    11. 말을 반복하지 마세요.
    12. 대화기록이 있다면, 활용해서 어색하지 않은 대답을 하세요.
    </답변 가이드>
    
    사용자 질문:
    {question}

    답변:
    """
    )

    return prompt | llm | StrOutputParser()


def create_industry_general_chain() -> Runnable:
    """Create a chain for general industry questions"""
    prompt = ChatPromptTemplate.from_template(
        """
    당신은 요식업 컨설팅, 브랜딩 전문 회사 창플의 대표 한범구의 AI Clone입니다.
 
    구체적인 추천보단, 폭 넓은 원칙을 제시하세요. 업계의 큰 변동성과 비즈니스 핵심을 설명하세요.

    사용자 정보:
    {user_info}

    관련 에세이 (주요 답변 근거):
    {primary_context}
    
    창플 철학 참고 자료:
    {philosophy_context}

    예시 질문과 대답:
    {example}

    대화 기록:
    {chat_history}
      
    관련 에세이, 창플 철학 참고 자료, 예시 질문과 대답을 활용하여 사용자 질문에 답하세요.
    <답변 가이드>
    1. 비즈니스의 원칙과 업계의 큰 변동성을 설명하세요.
    2. 비슷한 유형의 일반적 질문들에 대해 창플의 철학을 설명하며 논하세요.
    4. 400 단어를 사용해서 답변하세요.
    6. 주어진 관련 에세이의 문체, 어투를 따라하세요.
    7. 업계 트렌드에 대한 일반론적 접근과 추측에 반발하세요.
    8. 단기적 트렌드보다 장기적 사업 방향을 강조하세요
    9. 유저 정보에 대해서 직접적으로 언급하지 마세요.
    10. 비유적 표현을 활용하세요.
    11. 말을 반복하지 마세요.
    12. 대화기록이 있다면, 활용해서 어색하지 않은 대답을 하세요.
    </답변 가이드>

    사용자 질문:
    {question}

    답변:
    """
    )

    return prompt | llm | StrOutputParser()


def create_changple_info_chain() -> Runnable:
    """Create a chain for questions about Changple itself"""
    # This chain primarily relies on the philosophy context
    prompt = ChatPromptTemplate.from_template(
        """
    당신은 요식업 컨설팅, 브랜딩 전문 회사 창플의 대표 한범구의 AI Clone입니다.
     
    **창플의 철학**과 접근방법에 대해 설명하세요. 당신의 답변은 회사의 가치와 방법, 그리고 목표를 포함합니다.

    사용자 정보:
    {user_info}

    관련 에세이 (창플 정보):
    {primary_context} 

    예시 질문과 대답:
    {example}

    대화 기록:
    {chat_history}
     
    관련 에세이, 예시 질문과 대답을 활용하여 사용자 질문에 답하세요.
    <답변 가이드>
    1. 창플의 철학과 방법, 창업에 대한 접근 방식에 대해 설명하세요.
    2. 창플의 가치와 창플이 어떻게 창업 초심자, 자영업자 들을 돕는지 말하세요.
    4. 400 단어를 사용해서 답변하세요.
    6. 주어진 관련 에세이의 문체, 어투를 따라하세요.
    7. 창플의 접근 방법에 대한 구체적인 예시를 포함하세요.
    8. 창플의 접근 방식을 생존 전략과 이어서 설명하세요.
    9. 유저 정보에 대해서 직접적으로 언급하지 마세요.
    10. 비유적 표현을 활용하세요.
    11. 말을 반복하지 마세요.
    12. 대화기록이 있다면, 활용해서 어색하지 않은 대답을 하세요.
    </답변 가이드>
  
    사용자 질문:
    {question}

    답변:
    """
    )

    return prompt | llm | StrOutputParser()


def create_default_chain() -> Runnable:
    """Create a default chain for unknown question categories"""
    # No context needed for the default chain
    prompt = ChatPromptTemplate.from_template(
        """
    당신은 요식업 컨설팅, 브랜딩 전문 회사 창플의 대표 한범구의 AI Clone입니다.
 
    사용자의 질문에 대한 답변을 알 수 없을 경우 "음, 잘 모르겠네요."라고 대답하고, 
    창업과 관련된 질문이라면 추가적으로 정보를 요청하세요.
    
    사용자 정보:
    {user_info}
    
    대화 기록:
    {chat_history}
    
    사용자 질문:
    {question}
    
    답변:
    """
    )

    return prompt | llm | StrOutputParser()


def format_docs(docs: Sequence[Document]) -> str:
    """Format retrieved documents into a string"""
    formatted_docs = []
    for doc in docs:
        metadata = doc.metadata
        post_id = metadata.get("post_id")

        # Get original content if post_id exists
        if post_id:
            original_content = get_post_content(post_id)
            formatted_docs.append(original_content)
        else:
            # Fallback to document content
            title = metadata.get("title", "No Title")
            formatted_docs.append(f"Title: {title}\n\nContent: {doc.page_content}")

    return "\n\n---\n\n".join(formatted_docs)


def handle_post_generation(
    input_data: Dict[str, Any],
    full_answer: str,
    memory: ConversationBufferMemory
) -> Dict[str, Any]:
    """스트리밍 완료 후 메모리 저장 및 사용자 정보 업데이트 처리"""
    # 최종 질문 (rephrased or original)
    final_question = input_data["question"]

    # 대화 기록 저장
    memory.save_context(
        {"question": final_question},
        {"answer": full_answer},
    )
    logger.info(f"Saved conversation to memory. Q: {final_question[:50]}..., A: {full_answer[:50]}...")

    # 사용자 정보 업데이트 시도
    current_user_info = input_data.get("user_info", {})
    logger.info("Attempting to update user information post-streaming.")
    updated_info = update_user_information(
        current_user_info, final_question # 업데이트는 최종 질문 기준
    )
    logger.info(f"Updated user_info post-streaming: {updated_info}")

    return {
        "answer": full_answer, # 전체 답변도 반환 (필요시)
        "updated_user_info": updated_info,
    }


def create_chain(
    llm: LanguageModelLike, retriever: BaseRetriever, memory: ConversationBufferMemory
) -> Runnable:
    """Create the main chain for processing user questions (streaming enabled, without postprocessing)."""
    # Create specialized chains for each category
    specific_advice_chain = create_specific_advice_chain()
    question_advice_chain = create_question_advice_chain()
    industry_general_chain = create_industry_general_chain()
    changple_info_chain = create_changple_info_chain()
    default_chain = create_default_chain()

    # Process user input
    def process_input(input_data):
        original_question = input_data["question"]
        user = input_data.get("user")
        user_info = input_data.get("user_info", {})

        # Load history from memory
        chat_history_messages = memory.load_memory_variables({})["chat_history"]
        logger.info(f"Loaded chat history: {chat_history_messages}")

        # Instead of counting messages, we can directly check if chat history is truly empty
        # This ensures we NEVER condense on first message
        if len(chat_history_messages) == 0:
            logger.info(
                "This is definitely the first message, using original question."
            )
            final_question = original_question
        else:
            # We have history, check if we have at least one COMPLETE message exchange
            # A complete exchange is a HumanMessage followed by an AIMessage
            has_complete_exchange = False
            for i in range(len(chat_history_messages) - 1):
                if (
                    type(chat_history_messages[i]).__name__ == "HumanMessage"
                    and type(chat_history_messages[i + 1]).__name__ == "AIMessage"
                ):
                    has_complete_exchange = True
                    break

            if has_complete_exchange:
                logger.info(
                    "Found at least one complete message exchange, attempting to rephrase."
                )
                condense_question_chain = (
                    CONDENSE_QUESTION_PROMPT | llm | StrOutputParser()
                ).with_config(run_name="CondenseQuestion")

                # Format chat history for the condense chain
                formatted_history = "\n".join(
                    [f"{type(m).__name__}: {m.content}" for m in chat_history_messages]
                )

                try:
                    final_question = condense_question_chain.invoke(
                        {
                            "chat_history": formatted_history,
                            "question": original_question,
                            "user_info": user_info,
                        }
                    )
                    logger.info(f"Rephrased question: {final_question}")
                except Exception as e:
                    logger.error(
                        f"Error rephrasing question: {e}. Using original question.",
                        exc_info=True,
                    )
                    final_question = original_question
            else:
                logger.info("No complete exchanges found, using original question.")
                final_question = original_question

        # User info is now passed directly, no need to fetch from model
        if user:
            logger.info(f"User object received: {user.username}")
        else:
            logger.info("No user object provided, proceeding as anonymous.")

        logger.info(f"Using provided user_info: {user_info}")

        # Determine category
        category = determine_category(final_question, user_info)
        logger.info(f"Determined category: {category}")

        # Filter retriever based on category
        if category in CATEGORIES:
            # Update the filter to only retrieve documents with matching notation
            retriever.search_kwargs["filter"] = {
                "notation": {
                    "$in": [
                        category,
                    ]
                }
            }
            logger.info(f"Set retriever filter: {retriever.search_kwargs['filter']}")
        else:
            # Reset or clear filter if category is unknown or not applicable
            if "filter" in retriever.search_kwargs:
                del retriever.search_kwargs["filter"]
            logger.info(
                "Category is unknown or not in CATEGORIES, filter removed/not applied."
            )

        # Return the minimal needed data
        # We need original_question only for memory saving
        return {
            "question": final_question,  # The ONLY question we'll use for answering
            "original_question": original_question,  # Prefix with _ to indicate internal use only
            "category": category,
            "user": user,
            "user_info": user_info,
        }

    # Update the retrieve_docs function to use the single question field
    def retrieve_docs(input_data):
        if input_data["category"] == "unknown":
            logger.info("Category is unknown, skipping document retrieval.")
            return {"primary_context": "", "philosophy_context": "", **input_data}

        query_to_use = input_data["question"]  # Single question field
        logger.info(f"Retrieving documents using question: {query_to_use[:50]}...")
        current_category = input_data["category"]
        original_filter = retriever.search_kwargs.get("filter", {})
        original_k = retriever.search_kwargs.get("k", 40)

        primary_docs = []
        philosophy_docs = []

        # 1. Retrieve documents based on current question and category (Primary Context)
        logger.info(
            f"Retrieving primary documents for category '{current_category}'..."
        )
        try:
            # Ensure filter is set for the current category
            if current_category in CATEGORIES:
                retriever.search_kwargs["filter"] = {
                    "notation": {"$in": [current_category]}
                }
                primary_docs = retriever.invoke(query_to_use)
                logger.info(f"Retrieved {len(primary_docs)} primary documents.")
                if not primary_docs:
                    logger.warning("No primary documents retrieved.")
            else:
                # If category is not standard, primary retrieval might not apply or filter needs reset
                if "filter" in retriever.search_kwargs:
                    del retriever.search_kwargs["filter"]
                logger.warning(
                    f"Skipping primary retrieval due to category: {current_category}"
                )

        except Exception as e:
            logger.error(f"Error during primary document retrieval: {e}", exc_info=True)

        # 2. Retrieve fixed 5 documents for "창플과 관련된 질문 대답" (Philosophy Context)
        fixed_category = "창플과 관련된 질문 대답"
        generic_query = f"질문 '{query_to_use}'에 도움이 되는 창플 회사 소개 및 철학"  # Generic query for philosophy docs
        logger.info(
            f"Retrieving fixed 5 philosophy documents for category '{fixed_category}'..."
        )
        try:
            # Temporarily override filter and k for fixed retrieval
            retriever.search_kwargs["filter"] = {"notation": {"$in": [fixed_category]}}
            retriever.search_kwargs["k"] = 3
            philosophy_docs = retriever.invoke(generic_query)
            logger.info(f"Retrieved {len(philosophy_docs)} fixed philosophy documents.")
        except Exception as e:
            logger.error(
                f"Error retrieving fixed philosophy documents: {e}", exc_info=True
            )
        finally:
            # IMPORTANT: Restore original retriever settings
            retriever.search_kwargs["filter"] = original_filter
            retriever.search_kwargs["k"] = original_k
            logger.info("Restored original retriever search_kwargs.")

        # 3. Format documents into separate contexts
        primary_context = format_docs(primary_docs) if primary_docs else ""
        philosophy_context = format_docs(philosophy_docs) if philosophy_docs else ""

        logger.info(
            f"Primary context length: {len(primary_context)}, Philosophy context length: {len(philosophy_context)}"
        )

        return {
            "primary_context": primary_context,
            "philosophy_context": philosophy_context,
            **input_data,
        }

    # Define the branch logic based on category but don't add examples in each branch
    # They're already added by the previous step
    branch = RunnableBranch(
        (
            lambda x: x["category"] == "창플의 구체적 조언",
            specific_advice_chain,  # Example already in 'example' field
        ),
        (
            lambda x: x["category"] == "창플의 질문과 조언",
            question_advice_chain,  # Example already in 'example' field
        ),
        (
            lambda x: x["category"] == "창플의 업계 일반적 질문 대답",
            industry_general_chain,  # Example already in 'example' field
        ),
        (
            lambda x: x["category"] == "창플과 관련된 질문 대답",
            changple_info_chain,  # Example already in 'example' field
        ),
        default_chain,
    )

    # Radically simplify the chain structure
    chain = (
        RunnableLambda(process_input).with_config(run_name="ProcessInput")
        | RunnableLambda(retrieve_docs).with_config(run_name="RetrieveDocs")
        | RunnablePassthrough.assign(
            # memory.chat_memory.messages 를 직접 사용하여 현재 스냅샷을 전달
            chat_history=lambda _: "\n".join(
                [
                    (f"사용자: {msg.content}" if type(msg).__name__ == "HumanMessage" else f"AI: {msg.content}")
                    for msg in memory.chat_memory.messages
                ]
            ),
            example=lambda x: EXAMPLE_QA_MAP.get(x["category"], ""),
            # primary_context, philosophy_context 는 retrieve_docs 에서 이미 추가됨
        ).with_config(run_name="PrepareContext")
        | branch.with_config(run_name="ExecuteBranch") # 최종 LLM 호출 (스트리밍 시작점)
    )

    return chain
