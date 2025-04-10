import csv
import os

import pandas as pd
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# Set your OpenAI API key
# os.environ["OPENAI_API_KEY"] = "your_openai_api_key_here"

# Define the example Q&A for each category
EXAMPLE_QA_MAP = {
    "창플의 구체적 조언": """
Q. 30대 초반 남성인데, 분식집을 창업하려고 합니다. 자본금은 5천만원 정도 있고, 프랜차이즈로 시작하려고 하는데 어떤 점을 고려해야 할까요? 아이는 없고 사업에 온전히 시간을 할애할 수 있습니다.

A. 분식집창업은 대표적인 상권입지가 중요한 업종입니다. 특별히 찾아가서 먹는 것이 아니라, 내가 다니는 입지에 눈으로 발로 걸치면 그곳에가서 부담없이 사먹는것이죠.. 분식뿐만 아니고 대부분의 부담없이 즐기는 저가커피,빵집,와플가게나 핫도그집들도 다 비슷하게 평수가 작아서 시설비는 적게 드는것처럼 보이지만, 사실 그 업종들은 점포구입비용(보증금+권리금)을 많이 써야 하는 업종들입니다. 지금 그런 업종으로 망하는 초보창업자들이 언제나 실패하는건 점포비용으로는 권리금도 없는 곳에 들어가고 프랜차이즈에서 자신들의 컨셉이라고 불리는 인테리어비용을 들여서 하다보니, 망하는것이죠.. 좋은 자리에 있어야 하는 업종인데 시설비용때문에 나쁜자리에 들어가는것이죠.. 창업자금 5천만원이면 프랜차이즈본사 인테리어비용에도 못미치는 비용입니다. 프랜차이즈를 하게 되면 결국 배달프랜차이즈를 하게 되는데 문제는 배달프랜차이즈는 사실상 물류공급유통회사이기 때문에 그에 맞게 원가율이 높아집니다. 원가율이 높아져서 35% 40%가 되면 배달관련비용 30%가 합해지게 되어 결국 남은 30%로 임대료내고 인건비주고 나면 사실상 남는게 없는 프랜차이즈의 노예가 될 가능성이 높습니다.

만약에 5천만원밖에 없다면, 동네상권에서 망한 식당을 보증금2천만원 권리금1천만원 총 3천만원짜리 식당을 인수해서, 안주를 떡볶이와 튀김류들을 같이 만들어내서 안주로서의 분식으로 접근하는것이 좋습니다. 창플에서 만든 브랜드인 레이디오분식과 크런디라는 브랜드를 참조해도 좋고, 망원동튀맥이라고 하는 매장의 모습도 참고하면 좋습니다. 분식을 빙자한 술집으로 하게 되면 어느동네던지 기본 테이블단가가 나오면서 사람을 덜쓰고도 생존할수 있습니다. 분식은 원가가 낮고 미리 끓여놓고 튀겨놓으면 사람인건비도 많이 안써도 되기 때문입니다. 아이가 없으시면 더더욱 저녁과 밤을 겸해서 다른 분식집들이 문닫을때 장사하면 오히려 경쟁자들이 없어서 더 잘될수도 있습니다.
""",
    "창플의 질문과 조언": """
Q. 돈까스집 창업을 생각 중인데 어떻게 시작해야 할까요?

A. 일반적으로 부담없이 먹거나 배달시켜먹는 저렴한 돈가스집을 이야기하는것인가요? 아니면 차타고 와서 먹고 가는 경양식집돈가스를 얘기하는건가요? 아니면 외식성격으로 찾아와서 먹는 일본식 두꺼운 돈가스집을 이야기하시는 건가요?

일반적으로 같은 돈가스집이라고해도 부담없이 먹는 돈가스는 상권입지가 중요합니다. 가성비가 좋아야 하고 남녀노소 만족스러워야 하기 때문에 대중적인 맛을 유지를 잘해야 합니다. 상권입지가 좋으려면 점포구입비용에 더 투자를 해야 합니다 보증금과 권리금을 합한 금액이 최소 1억정도는 되어야 합니다. 그렇게 안되면 매출이 꾸준하지 않고 많이 나오는날은 많이 나오고 안나오는 날은 안나오는 편차가 있는 매출이 나게 됩니다. 그렇게 되면 고정비는 그대로인데 매출이 편차가 나면 문제가 생기죠.. 그렇게 입지가 안좋으면 결국 배달에 의존하게 되고, 배달에 의존하게 되면 30%의 수수료를 또 감당해야 하는데 그렇게 되면 매출은 나오는데 안남게 되는 상황도 발생합니다. 그래서 부담없이 먹는 돈가스집을 하려면 최소 2억이상의 투자금을 준비하셔야 합니다.

찾아오는 스타일의 우리집만의 외식형 돈가스집이라면 오히려 단가도 더 올려도 되고 찾아오기 때문에 입지가 꼭 좋지 않아도 됩니다. 

다만, 사람들이 몰리는 집객상권에는 있어야 합니다. 동네상권으로는 사람들이 안찾아오니.. 각 지역별 사람들이 모이는 곳에 들어가되 좋은입지에 들어가지 말고 온라인입지를 키워서 그곳으로 오게 하는 전략이 필요합니다.

돈가스클럽처럼 경양식돈가스같은 경우는, 해장국이나 설렁탕 입지에 들어가야 합니다. 차로 이동하면서 먹는 고객들을 대상으로 하기 때문에 주차와 평수에도 신경을 써야 합니다. 

결론적으로 같은 돈가스집이라고 해도, 창업비용이 작으면 가성비로 남녀노소 다 좋아하는 돈가스집을 하면 안됩니다. 오히려 돈가스의 퀄리티와 주류를 동반한 머무를수 있는 요소를 가지고 공간기획까지 들어가서 오고싶은곳을 만드는것이 가장 안전한 방법입니다.

항상 초보들은 본인들이 초보이기 때문에 가성비 부담없는 음식을 하려 하지만, 가성비에 부담없는 음식을 파는 평식업은 대기업과 큰 프랜차이즈들의 영역입니다. 우린 틈새로 가야 내가 가진 작은 창업비용으로 생존할수 있습니다.
""",
    "창플의 업계 일반적 질문 대답": """
Q. 요즘 트렌드인 식당 업종은 무엇인가요?

A. 창플에서는 트랜드를 말하지 않습니다. 트렌드는 그 트렌드를 이용해서 수익을 창출하려는 사업가들의 상술에 불과합니다. 트렌드보다는 방향성에 주목합니다. 

가령 지금은 아주 초가성비로 가던지, 아니면 확실하게 소비를 자랑할수 있는곳으로 가던가 소비의 방향이 확실합니다.

그러면 초가성비로 트랜드를 이끄는 브랜드가 있을것이고, 소비를 자랑할수 있는 그런 브랜딩을 통해서 이끄는 브랜드가 있을것이고, 기타 다른 브랜드들이 있을겁니다.

초보창업자들은 그 방향성에 대한 생각을 안하고 그런 방향성에 부합하는 브랜드를 보고 그대로 따라가는 경향이 있습니다 그렇게 트랜드라는 이유로 그 브랜드자체를 따라가면 순식간에 컨텐츠소비가 끝나면서 공멸하는 경우들이 많습니다. 앞서 이야기한 칼럼들을 살펴보시고, 현재 시장의 모습과 전망을 알아가시길 바랍니다.
""",
    "창플과 관련된 질문 대답": """
Q. 창플은 어떤 일을 하는 회사인가요?

A. 창플은 초보창업자들의 생존을 위해 존재하는 회사입니다. 생존포인트를 연구하고, 그에 따른 브랜드를 만들고(아키프로젝트) 또한 그렇게 만든 브랜드를 또다른 초보창업자들이 할수 있게(팀비즈니스)전수창업식의 창업도 추천하고 있습니다.

창플의 생존방식은 명확합니다. 창플의 생존공식이 담긴 파전에 막걸리집이론을 참조하시면 알겠지만, 중간유통거품없이 원재료를 받아서 원가를 낮추고, 인테리어같은 값비싼 비용을 들이지 않고 실제 고객들에게 임팩트를 주는 vmd작업을 통해서 시설비용을 아끼고. 사장 본인의 몸을 갈아넣어서 직원및 알바1명으로 같이 창업을 하면 결코 망하지 않는다는 것이죠

브랜드나 아이템 업종이 문제가 아니라, 밥집을 하던지 술집을 하던지 고깃집을 하던지 그 어떤 업을 하던지 장사구조를 그렇게 잡고 자신이 감당할수 있는 범위의 창업비용을 가지고, 내몸을 이용해서 생존할수 있게 해야 한다는것입니다.

그에 대한 사례가 창플카페에는 무수히 많습니다. 매출은 적어도 결코 죽지 않는다는 사례를 보여주며, 초보들의 첫창업을 망하지 않게 돕는 그런 회사입니다.
""",
}

# Categories to evaluate in order
CATEGORIES = [
    "창플의 구체적 조언",
    "창플의 질문과 조언",
    "창플의 업계 일반적 질문 대답",
    "창플과 관련된 질문 대답",
]

# Get Google API key (if needed)
google_api_key = os.getenv("GOOGLE_API_KEY")

# Initialize GPT-4o model
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    google_api_key=google_api_key,
)


# Create evaluation prompts for each category
def create_category_chain(category):
    """Create an evaluation chain for a specific category"""

    if category == "창플의 구체적 조언":
        prompt = ChatPromptTemplate.from_template(
            """
You are a content evaluator for Q&A creation.

Background information:
Changple (창플) is a consulting and branding company for novice restaurant startups.

Task: Evaluate if the given content is SPECIFICALLY useful for creating Q&A pairs about '{category}'.

For this category, content must:
1. Contain SPECIFIC, ACTIONABLE ADVICE about restaurant business or entrepreneurship
2. Include concrete numbers, calculations, or business logic
3. Discuss practical operational strategies, investment decisions, or financial considerations
4. Address a specific business scenario with detailed recommendations
5. Be substantial enough to generate a detailed response with practical steps

Example Q&A for reference:
{example_qa}

Content to evaluate:
{content}

Evaluate STRICTLY if the content meets ALL criteria for this category.
If the content meets ALL the criteria, respond with exactly: "yes"
If the content fails to meet ANY of the criteria, respond with exactly: "no"

Respond with only "yes" or "no".
"""
        )
    elif category == "창플의 질문과 조언":
        prompt = ChatPromptTemplate.from_template(
            """
You are a content evaluator for Q&A creation.

Background information:
Changple (창플) is a consulting and branding company for novice restaurant startups.

Task: Evaluate if the given content is SPECIFICALLY useful for creating Q&A pairs about '{category}'.

For this category, content must:
1. Present a scenario that would benefit from MULTIPLE PERSPECTIVES or business approaches
2. Be suitable for generating clarifying questions before offering advice
3. Allow for discussion of different business models or conditions
4. Be suitable for conditional advice based on different circumstances

Example Q&A for reference:
{example_qa}

Content to evaluate:
{content}

Evaluate STRICTLY if the content meets ALL criteria for this category.
If the content meets ALL the criteria, respond with exactly: "yes"
If the content fails to meet ANY of the criteria, respond with exactly: "no"

Respond with only "yes" or "no".
"""
        )
    elif category == "창플의 업계 일반적 질문 대답":
        prompt = ChatPromptTemplate.from_template(
            """
You are a content evaluator for Q&A creation.

Background information:
Changple (창플) is a consulting and branding company for novice restaurant startups.

Task: Evaluate if the given content is SPECIFICALLY useful for creating Q&A pairs about '{category}'.

For this category, content must:
1. Discuss market trends, dynamics, or industry direction
2. Examine fundamental business principles or philosophy
3. Challenge common assumptions about industry trends

Example Q&A for reference:
{example_qa}

Content to evaluate:
{content}

Evaluate STRICTLY if the content meets ALL criteria for this category.
If the content meets ALL the criteria, respond with exactly: "yes"
If the content fails to meet ANY of the criteria, respond with exactly: "no"

Respond with only "yes" or "no".
"""
        )
    else:  # "창플과 관련된 질문 대답"
        prompt = ChatPromptTemplate.from_template(
            """
You are a content evaluator for Q&A creation.

Background information:
Changple (창플) is a consulting and branding company for novice restaurant startups.

Task: Evaluate if the given content is SPECIFICALLY useful for creating Q&A pairs about '{category}'.

For this category, content must:
1. EXPLICITLY mention or directly relate to Changple's philosophy, methods, services, or approach
2. Contain information about how Changple helps entrepreneurs or its business model
3. Discuss Changple's values, methodology, or company mission

Example Q&A for reference:
{example_qa}

Content to evaluate:
{content}

Evaluate STRICTLY if the content meets ALL criteria for this category.
If the content meets ALL the criteria, respond with exactly: "yes"
If the content fails to meet ANY of the criteria, respond with exactly: "no"

Respond with only "yes" or "no".
"""
        )

    return prompt | llm | StrOutputParser()


# Create evaluation chains for each category
category_chains = {category: create_category_chain(category) for category in CATEGORIES}


def evaluate_content(content):
    """
    Evaluate if content is useful for creating Q&A about each category

    Args:
        content (str): The content to evaluate

    Returns:
        list: List of categories that the content is useful for, or ["none"] if no category matches
    """
    matches = []

    # Evaluate for each category
    for category in CATEGORIES:
        result = category_chains[category].invoke(
            {
                "content": content,
                "example_qa": EXAMPLE_QA_MAP[category],
                "category": category,
            }
        )

        if result.strip().lower() == "yes":
            matches.append(category)

    # If no categories match, return "none"
    if not matches:
        return ["none"]

    return matches


def summary_and_keywords(content):
    """
    Summarize the content and extract keywords

    Args:
        content (str): The content to summarize and extract keywords from

    Returns:
        tuple: (summarized_content, list of keywords)
    """
    # Define the prompt for summarization and keyword extraction
    prompt = ChatPromptTemplate.from_template(
        """
당신은 요식업 창업 컨설팅, 브랜딩 회사인 창플의 유능한 AI 어시스턴스입니다.
당신의 할 일은 주어진 컨텐츠를 **한 문장**으로 요약하고, 키워드를 추출하는 것입니다.

분석할 컨텐츠:
{content}

1. First, provide a concise one sentence summary of the content that preserves the key advice, insights, and practical information.
2. Then, extract a list of 10 keywords that best represent the main topics in the content.
   Focus on business-related terms, restaurant industry concepts, entrepreneurship topics and brand names.

Output format:
SUMMARY:
[your summary here]

KEYWORDS:
[keyword1, keyword2, keyword3, ... ]
"""
    )

    # Create chain for summarization and keyword extraction
    summary_chain = prompt | llm | StrOutputParser()

    try:
        # Invoke the chain
        result = summary_chain.invoke({"content": content})

        # Parse the result
        summary_text = ""
        keywords = []

        if "SUMMARY:" in result and "KEYWORDS:" in result:
            summary_section = result.split("KEYWORDS:")[0].strip()
            keywords_section = result.split("KEYWORDS:")[1].strip()

            # Extract summary
            summary_text = summary_section.replace("SUMMARY:", "").strip()

            # Extract keywords
            keywords_raw = keywords_section.strip()
            # Clean up keywords (handle various formats like comma-separated, bullet points, etc.)
            keywords = [
                k.strip()
                for k in keywords_raw.replace("[", "").replace("]", "").split(",")
            ]
            # Filter out empty strings
            keywords = [k for k in keywords if k]
        else:
            # Fallback if the format is unexpected
            summary_text = content
            keywords = []

        return summary_text, keywords
    except Exception as e:
        # Log the error and return the original content with empty keywords
        print(f"Error in summary_and_keywords: {e}")
        raise ValueError(f"Error in summary_and_keywords: {e}")


# Example usage
if __name__ == "__main__":
    pass
    # CSV file evaluation
    # csv_file = "navercafe_essays_bum9.csv"
    # if os.path.exists(csv_file):
    #     evaluate_csv_file(csv_file)
    # else:
    #     print(f"CSV file not found: {csv_file}")

    # # Interactive mode
    # print("\nInteractive Content Evaluator")
    # print("Enter content to evaluate (type 'exit' to quit):")

    # while True:
    #     user_input = input("\nContent: ")
    #     if user_input.lower() == "exit":
    #         break

    #     result = evaluate_content(user_input)
    #     print(f"Evaluation result: {result}")
