"""
Gemini Batch API for summarization (50% cost savings).

https://ai.google.dev/gemini-api/docs/batch-api
"""

import json
import logging
from typing import List, Optional

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Note: google-generativeai package needs to be installed for batch API
# The batch API is different from the regular API


def build_summarization_prompt(title: str, content: str) -> str:
    """Build the prompt for summarization."""
    return f"""당신은 주어진 문장을 요약하고, 키워드를 추출하고, 해당 문서를 리트리벌 할 수 있는 쿼리를 생성하는 AI 어시스턴트입니다.

요약: 주어진 본문을 약 100 단어를 활용해서 요약하세요. 최소 5문장 이상 작성하고, 요약의 끝맺음을 확실하게 하세요.
키워드: 본문에서 언급된 브랜드 명, 서비스 명, 전문 용어, 핵심 주제, 목적 등의 핵심 키워드 10개를 추출하세요.
리트리벌 쿼리: 초보 창업자가 창업 컨설턴트에게 질문할 법한 리트리벌 쿼리 5개를 생성하세요.(본문에 나오는 수치, 음식 이름, 메뉴 명 등 활용) 리트리벌 쿼리들은 해당 본문을 리트리벌 할 수 있어야 합니다. 문장이 아니라 최대 5개의 단어를 나열하세요.

응답은 반드시 다음 JSON 형식으로 작성하세요:
{{
    "summary": "요약 텍스트",
    "ten_keywords": ["키워드1", "키워드2", ...],
    "five_retrieval_queries": ["쿼리1", "쿼리2", ...]
}}

---

제목:{title}
{content}"""


def submit_summarization_batch(posts: list) -> Optional[str]:
    """
    Submit batch job to Gemini Batch API.

    Args:
        posts: List of NaverCafeData objects

    Returns:
        job_name for polling, or None if failed

    Note: Gemini Batch API provides 50% cost savings with 24-hour SLA.
    """
    try:
        import google.generativeai as genai

        # Configure the API
        genai.configure(api_key=settings.GOOGLE_API_KEY)

        # Prepare inline requests
        requests = []
        for post in posts:
            prompt = build_summarization_prompt(post.title, post.content)
            requests.append(
                {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generation_config": {"response_mime_type": "application/json"},
                }
            )

        # Submit batch (50% cost, 24-hour SLA)
        job = genai.batches.create(model="gemini-2.0-flash", requests=requests)

        logger.info(f"Submitted Gemini batch job: {job.name}")
        return job.name

    except ImportError:
        logger.error("google-generativeai package not installed")
        return None
    except Exception as e:
        logger.error(f"Failed to submit Gemini batch job: {e}")
        return None


def check_summarization_batch(job_name: str) -> tuple[str, Optional[list]]:
    """
    Check status of a Gemini batch job.

    Args:
        job_name: The job name returned from submit_summarization_batch

    Returns:
        Tuple of (status, results):
        - status: "processing", "completed", "failed"
        - results: List of dicts with summary, keywords, questions if completed
    """
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.GOOGLE_API_KEY)

        job = genai.batches.get(job_name)

        if job.state == "JOB_STATE_SUCCEEDED":
            results = []
            for response in job.response.inline_responses:
                try:
                    # Parse JSON response
                    text = response.response.candidates[0].content.parts[0].text
                    data = json.loads(text)
                    results.append(
                        {
                            "summary": data.get("summary", ""),
                            "keywords": data.get("ten_keywords", []),
                            "questions": data.get("five_retrieval_queries", []),
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to parse batch response: {e}")
                    results.append(None)

            return "completed", results

        elif job.state in ("JOB_STATE_FAILED", "JOB_STATE_CANCELLED"):
            logger.error(f"Batch job failed: {job.state}")
            return "failed", None

        else:
            # Still processing
            return "processing", None

    except ImportError:
        logger.error("google-generativeai package not installed")
        return "failed", None
    except Exception as e:
        logger.error(f"Failed to check Gemini batch job: {e}")
        return "failed", None


def process_summarization_results(batch_job, results: list) -> int:
    """
    Process summarization results and update database.

    Args:
        batch_job: BatchJob model instance
        results: List of result dicts from check_summarization_batch

    Returns:
        Number of successfully processed posts
    """
    from src.scraper.models import NaverCafeData

    post_ids = batch_job.post_ids
    processed_count = 0

    for i, (post_id, result) in enumerate(zip(post_ids, results)):
        if result is None:
            logger.warning(f"Skipping post {post_id} - no result")
            continue

        try:
            post = NaverCafeData.objects.get(post_id=post_id)
            post.summary = result["summary"]
            post.keywords = result["keywords"]
            post.possible_questions = result["questions"]
            post.save(update_fields=["summary", "keywords", "possible_questions"])
            processed_count += 1
            logger.info(f"Updated post {post_id} with summarization results")
        except NaverCafeData.DoesNotExist:
            logger.error(f"Post {post_id} not found in database")
        except Exception as e:
            logger.error(f"Failed to update post {post_id}: {e}")

    # Update batch job status
    batch_job.status = "completed"
    batch_job.completed_at = timezone.now()
    batch_job.save()

    return processed_count
