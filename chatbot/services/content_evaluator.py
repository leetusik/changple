import csv
import json
import os
from typing import List

import nest_asyncio
import pandas as pd
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

from .chain import load_llm

nest_asyncio.apply()
# langchain-google-genai 라이브러리가 내부적으로 비동기(asyncio) 기능을 사용하기 때문에 nest-asyncioo 설치

load_dotenv()

# Get Google API key (if needed)
google_api_key = os.getenv("GOOGLE_API_KEY")

llm = load_llm()


# 2. ContentOutput 모델 수정
class ContentOutput(BaseModel):

    summary: str = Field(description="본문 요약. 약 200 토큰 활용")
    keywords: List[str] = Field(
        description="언급된 브랜드 명, 서비스 명, 핵심 주제 등 키워드 10개",
        min_items=10,
        max_items=10,
    )
    retrieval_queries: List[str] = Field(
        description="리트리벌 쿼리 3개. 문장보다 약 3개의 단어 나열. 본문에서 나온 수치도 활용.",
        min_items=3,
        max_items=3,
    )


def summary_and_keywords(content):
    """
    Summarize the content and extract keywords using structured output

    Args:
        content (str): The content to summarize and extract keywords from

    Returns:
        tuple: (summary_text, keywords_list, questions_list)
               Returns (None, None, None) on failure.
    """
    # Define the prompt for summarization and keyword extraction
    prompt = ChatPromptTemplate.from_template(
        """
당신은 주어진 문장을 요약하고, 키워드를 추출하고, 해당 문서를 리트리벌 할 수 있는 쿼리를 생성하는 AI 어시스턴트입니다.

요약: 주어진 본문을 약 200 토큰을 활용해서 요약하세요. 작성자가 직접 요약한 것처럼 작성하세요.
키워드: 본문에서 언급된 브랜드 명, 서비스 명, 전문 용어, 핵심 주제 등의 키워드 10개를 추출하세요.
리트리벌 쿼리: 본문이 더욱 잘 사용자에 의해 리트리벌 될 수 있도록 리트리벌 쿼리 3개를 생성하세요.(본문에 나오는 수치도 활용) 문장이 아니라 약 3개의 단어를 나열하세요.

---

{content}
"""
    )

    # 3. 체인 수정: .with_structured_output 사용
    # schema=ContentOutput 대신 ContentOutput 자체를 전달해도 됩니다.
    # include_raw=True를 설정하면 파싱 실패 시 원본 LLM 출력을 볼 수 있습니다.
    structured_llm = llm.with_structured_output(schema=ContentOutput, include_raw=True)
    chain = prompt | structured_llm

    try:
        # Invoke the chain
        result = chain.invoke({"content": content})

        # 4. 결과 처리 수정
        if isinstance(result, dict) and "parsed" in result:
            # include_raw=True를 사용했을 때의 처리
            parsed_output = result.get("parsed")
            if parsed_output and isinstance(parsed_output, ContentOutput):
                # Pydantic 모델 객체에서 직접 속성 접근
                summary_text = parsed_output.summary
                keywords = parsed_output.keywords
                possible_questions = parsed_output.retrieval_queries
                # 결과 반환 시 questions도 함께 반환하도록 수정 (필요에 따라)
                return summary_text, keywords, possible_questions
            else:
                # 파싱 실패 또는 예상치 못한 형식
                raw_output = result.get("raw")
                error_msg = f"Failed to parse LLM output into ContentOutput model. Raw output: {raw_output}"
                print(error_msg)  # 혹은 logger 사용
                raise ValueError(error_msg)
        elif isinstance(result, ContentOutput):
            # include_raw=False (기본값)를 사용했을 때의 처리
            summary_text = result.summary
            keywords = result.keywords
            possible_questions = result.retrieval_queries
            return summary_text, keywords, possible_questions
        else:
            # 예상치 못한 결과 타입
            error_msg = f"Unexpected result type from chain: {type(result)}"
            print(error_msg)  # 혹은 logger 사용
            raise ValueError(error_msg)

    except Exception as e:
        # Log the error and raise a specific ValueError or return None
        error_info = f"Error in summary_and_keywords: {e}"
        print(error_info)  # 혹은 logger 사용
        # 여기서 에러를 다시 raise 하거나, (None, None, None) 등을 반환하여
        # 호출하는 쪽(예: ingest.py)에서 처리하도록 할 수 있습니다.
        # ingest.py의 SkipDocumentError 처리를 유지하려면 여기서 ValueError를 raise하는 것이 적합합니다.
        raise ValueError(error_info)
