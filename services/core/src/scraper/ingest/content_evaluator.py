"""
Content evaluation using LLM for summarization and keyword extraction.
"""

import logging
import time
from typing import List, Tuple

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def load_llm(model_name: str = "gemini-2.5-flash", temperature: float = 0.0):
    """Load Google Gemini LLM with specified model and temperature."""
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
    )


# Initialize LLM models
llm = load_llm(model_name="gemini-2.5-flash")
fast_llm = load_llm(model_name="gemini-2.0-flash")


class ContentOutput(BaseModel):
    """Output schema for content summarization and keyword extraction."""

    summary: str = Field(description="본문 요약. 약 100 단어 활용. 최소 5문장 이상.")
    ten_keywords: List[str] = Field(
        description="언급된 브랜드 명, 서비스 명, 핵심 주제, 음식 이름 등 키워드 10개",
    )
    five_retrieval_queries: List[str] = Field(
        description="리트리벌 쿼리 5개. 문장보다 최대 5개의 단어 나열. 구체적 수치, 음식 이름, 메뉴 명등 활용",
    )


def summary_and_keywords(
    content: str,
    max_retries: int = 2,
    initial_backoff: int = 2,
) -> Tuple[str, List[str], List[str]]:
    """
    Summarize the content and extract keywords using structured output with retry logic.

    Args:
        content: The content to summarize and extract keywords from
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds (increases exponentially)

    Returns:
        tuple: (summary_text, keywords_list, questions_list)

    Raises:
        ValueError: If all attempts fail after retries
    """
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
            logger.info(f"Attempt {attempt}/{max_retries}: Invoking main LLM chain...")
            result = chain.invoke({"content": content})
            logger.info(
                f"Attempt {attempt}/{max_retries}: Main LLM chain invocation successful."
            )

            parsed_output = _extract_parsed_output(result)
            if parsed_output:
                return (
                    parsed_output.summary,
                    parsed_output.ten_keywords,
                    parsed_output.five_retrieval_queries,
                )

            error_msg = f"Failed to parse main LLM output. Raw: {result.get('raw') if isinstance(result, dict) else result}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        except (ValueError, Exception) as e:
            if attempt == 1:
                error_type = type(e).__name__
                logger.warning(
                    f"Attempt {attempt}/{max_retries}: Main LLM failed with {error_type}. Error: {e}. Falling back to fast LLM."
                )
                last_exception = e

                # Fallback attempt with fast LLM
                try:
                    logger.info("Invoking fast LLM chain...")
                    fallback_result = fast_chain.invoke({"content": content})
                    logger.info("Fast LLM chain invocation successful.")

                    parsed_output = _extract_parsed_output(fallback_result)
                    if parsed_output:
                        return (
                            parsed_output.summary,
                            parsed_output.ten_keywords,
                            parsed_output.five_retrieval_queries,
                        )

                    error_msg = f"Failed to parse fast LLM fallback output. Raw: {fallback_result.get('raw') if isinstance(fallback_result, dict) else fallback_result}"
                    logger.error(error_msg)
                    last_exception = ValueError(error_msg)

                except Exception as fallback_e:
                    logger.error(f"Error during fast LLM fallback: {fallback_e}")
                    last_exception = fallback_e

                if attempt < max_retries:
                    backoff_time = initial_backoff * (2 ** (attempt - 1))
                    logger.info(f"Retrying main LLM in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                    continue
                else:
                    break
            else:
                if isinstance(e, ValueError):
                    logger.error(f"Unrecoverable error on attempt {attempt}: {e}")
                    last_exception = e
                    break
                else:
                    logger.error(f"Error on attempt {attempt}: {e}")
                    last_exception = e

                if attempt < max_retries:
                    backoff_time = initial_backoff * (2 ** (attempt - 1))
                    logger.info(f"Retrying main LLM in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error("Max retries reached for main LLM.")
                    break

    error_msg = f"Failed to generate structured output after {max_retries} attempt(s)."
    if last_exception:
        error_msg += f" Last error: {last_exception}"
    logger.error(error_msg)
    raise ValueError(error_msg)


def _extract_parsed_output(result) -> ContentOutput | None:
    """Extract ContentOutput from LLM result."""
    try:
        if isinstance(result, dict) and "parsed" in result:
            parsed_output = result.get("parsed")
            if parsed_output and isinstance(parsed_output, ContentOutput):
                return parsed_output
        elif isinstance(result, ContentOutput):
            return result
        return None
    except Exception as e:
        logger.error(f"Error extracting parsed output: {e}")
        return None
