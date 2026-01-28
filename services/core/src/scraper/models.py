"""
Scraper models for Changple Core service.
"""

from django.db import models

from src.common.models import CommonModel


class NaverCafeData(CommonModel):
    """
    네이버 카페 게시글 원문 모델
    """

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=200)
    content = models.TextField()
    author = models.CharField(max_length=200)
    published_date = models.DateTimeField(db_index=True)
    post_id = models.IntegerField(unique=True)
    notation = models.JSONField(null=True, blank=True)
    keywords = models.JSONField(null=True, blank=True)
    summary = models.TextField(null=True, blank=True)
    possible_questions = models.JSONField(
        null=True,
        blank=True,
        help_text="원문이 대답이 될 수 있는 예상 질문 리스트",
    )
    ingested = models.BooleanField(default=False)

    def get_url(self) -> str:
        return f"https://cafe.naver.com/cjdckddus/{self.post_id}"

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Naver Cafe Data"
        verbose_name_plural = "Naver Cafe Data"
        indexes = [
            models.Index(fields=["author"]),
            models.Index(fields=["ingested"]),
        ]


class PostStatus(CommonModel):
    """
    NaverCafeData 수집 상태를 나타냄. SAVED, DELETED, ERROR 세 가지로 구분
    """

    STATUS_CHOICES = [
        ("DELETED", "Deleted"),
        ("ERROR", "Error"),
        ("SAVED", "Saved"),
    ]

    post_id = models.IntegerField(unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Post Status"
        verbose_name_plural = "Post Statuses"
        indexes = [
            models.Index(fields=["post_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Post {self.post_id} - {self.get_status_display()}"


class AllowedAuthor(models.Model):
    """벡터화 게시글 작성자 명단(on/off)"""

    AUTHOR_GROUPS = [
        ("창플", "창플"),
        ("팀비즈니스_브랜드", "팀비즈니스 브랜드"),
        ("기타", "기타"),
    ]

    name = models.CharField(max_length=200, unique=True)
    author_group = models.CharField(
        max_length=50,
        choices=AUTHOR_GROUPS,
        default="창플",
        help_text="작성자 그룹",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="체크가 안되어있을 경우, 벡터화되지 않음(해당 작성자의 게시글 사용 안됨)",
    )

    class Meta:
        verbose_name = "Allowed Author"
        verbose_name_plural = "Allowed Authors"
        ordering = ["author_group", "name"]

    def __str__(self):
        return self.name


class GoodtoKnowBrands(models.Model):
    """Good to know brands for context"""

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(null=True, blank=True)
    is_goodto_know = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Good to Know Brand"
        verbose_name_plural = "Good to Know Brands"

    def __str__(self):
        return self.name


class BatchJob(CommonModel):
    """
    Track async batch jobs for Provider Batch APIs (50% cost savings).

    Gemini Batch API: Summarization jobs
    OpenAI Batch API: Embedding jobs
    """

    JOB_TYPE_CHOICES = [
        ("summarize", "Summarization"),
        ("embed", "Embedding"),
    ]
    PROVIDER_CHOICES = [
        ("gemini", "Google Gemini"),
        ("openai", "OpenAI"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("submitted", "Submitted"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    job_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Provider's job/batch ID (job_name for Gemini, batch_id for OpenAI)",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    post_ids = models.JSONField(
        default=list,
        help_text="List of NaverCafeData post_ids in this batch",
    )
    result_file = models.CharField(
        max_length=500,
        blank=True,
        help_text="Path to results file if file-based",
    )
    error_message = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Batch Job"
        verbose_name_plural = "Batch Jobs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["job_type", "status"]),
        ]

    def __str__(self):
        return f"{self.get_job_type_display()} ({self.provider}) - {self.status}"
