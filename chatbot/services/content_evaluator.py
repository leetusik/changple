import asyncio
import csv
import json
import logging
import os
import time
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
fast_llm = load_llm(model_name="gemini-2.0-flash")

logger = logging.getLogger(__name__)


# 2. ContentOutput 모델 수정
class ContentOutput(BaseModel):

    summary: str = Field(description="본문 요약. 약 100 단어 활용. 최소 5문장 이상.")
    ten_keywords: List[str] = Field(
        description="언급된 브랜드 명, 서비스 명, 핵심 주제, 음식 이름 등 키워드 10개",
    )
    five_retrieval_queries: List[str] = Field(
        description="리트리벌 쿼리 5개. 문장보다 최대 5개의 단어 나열. 구체적 수치, 음식 이름, 메뉴 명등 활용",
    )


async def summary_and_keywords(content, max_retries=2, initial_backoff=2):
    """
    Summarize the content and extract keywords using structured output (async version with timeout and fallback)

    Args:
        content (str): The content to summarize and extract keywords from
        max_retries (int): Maximum number of retry attempts
        initial_backoff (int): Initial backoff time in seconds (will increase exponentially)

    Returns:
        tuple: (summary_text, keywords_list, questions_list)
               Returns (None, None, None) on failure.
    """
    # Define the prompt for summarization and keyword extraction
    prompt = ChatPromptTemplate.from_template(
        """
당신은 주어진 문장을 요약하고, 키워드를 추출하고, 해당 문서를 리트리벌 할 수 있는 쿼리를 생성하는 AI 어시스턴트입니다.

요약: 주어진 본문을 약 100 단어를 활용해서 요약하세요. 최소 5문장 이상 작성하고, 요약의 끝맺음을 확실하게 하세요.
키워드: 본문에서 언급된 브랜드 명, 서비스 명, 전문 용어, 핵심 주제, 목적 등의 핵심 키워드 10개를 추출하세요.
리트리벌 쿼리: 초보 창업자가 창업 컨설턴트에게 질문할 법한 리트리벌 쿼리 5개를 생성하세요.(본문에 나오는 수치, 음식 이름, 메뉴 명 등 활용) 리트리벌 쿼리들은 해당 본문을 리트리벌 할 수 있어야 합니다. 문장이 아니라 최대 5개의 단어를 나열하세요.

---

{content}
"""
    )

    # Main LLM chain
    structured_llm = llm.with_structured_output(schema=ContentOutput, include_raw=True)
    chain = prompt | structured_llm

    # Fast LLM chain (for fallback)
    structured_fast_llm = fast_llm.with_structured_output(
        schema=ContentOutput, include_raw=True
    )
    fast_chain = prompt | structured_fast_llm

    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            # --- Attempt with main LLM ---
            logger.info(
                f"Attempt {attempt}/{max_retries}: Invoking main LLM chain (gemini-2.5-flash)... Timeout=30s"
            )
            result = await asyncio.wait_for(
                chain.ainvoke({"content": content}), timeout=30
            )
            logger.info(
                f"Attempt {attempt}/{max_retries}: Main LLM chain invocation successful."
            )

            # Process result
            if isinstance(result, dict) and "parsed" in result:
                parsed_output = result.get("parsed")
                if parsed_output and isinstance(parsed_output, ContentOutput):
                    summary_text = parsed_output.summary
                    ten_keywords = parsed_output.ten_keywords
                    five_retrieval_queries = parsed_output.five_retrieval_queries
                    return summary_text, ten_keywords, five_retrieval_queries
                else:
                    raw_output = result.get("raw")
                    error_msg = f"Failed to parse main LLM output. Raw: {raw_output}"
                    logger.error(error_msg)
                    raise ValueError(
                        error_msg
                    )  # Raise specific error for parsing failure
            elif isinstance(result, ContentOutput):
                summary_text = result.summary
                ten_keywords = result.ten_keywords
                five_retrieval_queries = result.five_retrieval_queries
                return summary_text, ten_keywords, five_retrieval_queries
            else:
                error_msg = (
                    f"Unexpected result type from main LLM chain: {type(result)}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)  # Raise specific error for unexpected type

        except asyncio.TimeoutError:
            logger.warning(
                f"Attempt {attempt}/{max_retries}: Main LLM timed out. Falling back to fast LLM (gemini-2.5-flash)."
            )
            last_exception = asyncio.TimeoutError(
                "Main LLM timed out after 30 seconds."
            )

            # --- Fallback Attempt with Fast LLM ---
            try:
                logger.info("Invoking fast LLM chain...")
                # No timeout applied to fallback, or a different one could be set
                fallback_result = await fast_chain.ainvoke({"content": content})
                logger.info("Fast LLM chain invocation successful.")

                # Process fallback result
                if isinstance(fallback_result, dict) and "parsed" in fallback_result:
                    parsed_output = fallback_result.get("parsed")
                    if parsed_output and isinstance(parsed_output, ContentOutput):
                        summary_text = parsed_output.summary
                        ten_keywords = parsed_output.ten_keywords
                        five_retrieval_queries = parsed_output.five_retrieval_queries
                        return (
                            summary_text,
                            ten_keywords,
                            five_retrieval_queries,
                        )  # Success on fallback
                    else:
                        raw_output = fallback_result.get("raw")
                        error_msg = f"Failed to parse fast LLM fallback output. Raw: {raw_output}"
                        logger.error(error_msg)
                        raise ValueError(
                            error_msg
                        )  # Raise specific error for parsing failure on fallback
                elif isinstance(fallback_result, ContentOutput):
                    summary_text = fallback_result.summary
                    ten_keywords = fallback_result.ten_keywords
                    five_retrieval_queries = fallback_result.five_retrieval_queries
                    return (
                        summary_text,
                        ten_keywords,
                        five_retrieval_queries,
                    )  # Success on fallback
                else:
                    error_msg = f"Unexpected result type from fast LLM chain: {type(fallback_result)}"
                    logger.error(error_msg)
                    raise ValueError(
                        error_msg
                    )  # Raise specific error for unexpected type on fallback

            except Exception as fallback_e:
                logger.error(f"Error during fast LLM fallback: {fallback_e}")
                last_exception = (
                    fallback_e  # Update last exception to the fallback error
                )
                break  # Exit retry loop after fallback failure

            # If fallback processing failed (e.g., ValueError from parsing), the exception is caught below
            # and the loop will break.

        except (
            ValueError
        ) as parse_or_type_e:  # Catch parsing/type errors from main or fallback
            logger.error(
                f"Attempt {attempt}/{max_retries}: Unrecoverable error: {parse_or_type_e}"
            )
            last_exception = parse_or_type_e
            break  # Exit loop immediately on parsing or type errors

        except Exception as e:
            # Handle other exceptions from main LLM call (non-timeout, non-parsing)
            logger.error(
                f"Attempt {attempt}/{max_retries}: Error invoking main LLM: {e}"
            )
            last_exception = e

            if attempt < max_retries:
                backoff_time = initial_backoff * (2 ** (attempt - 1))
                logger.info(f"Retrying main LLM in {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
                continue  # Continue to next attempt with main LLM
            else:
                logger.error(
                    "Max retries reached for main LLM after non-timeout error."
                )
                break  # Exit loop if max retries reached

    # --- End of Loop ---
    # If loop finished without returning (i.e., all attempts/fallback failed)
    error_msg = f"Failed to generate structured output after {attempt} attempt(s)."
    if last_exception:
        error_msg += f" Last error: {last_exception}"
    logger.error(error_msg)  # Log final failure
    raise ValueError(error_msg)  # Raise final error
