from django.db import models


# Create your models here.
class NaverCafeData(models.Model):
    title = models.CharField(max_length=200, null=False, blank=False)
    category = models.CharField(max_length=200, null=False, blank=False)
    content = models.TextField(null=False, blank=False)
    author = models.CharField(max_length=200, null=False, blank=False)
    published_date = models.CharField(
        max_length=200, null=True, blank=True
    )  # Store as original string from Naver
    url = models.URLField(unique=True, null=False, blank=False)
    post_id = models.IntegerField(null=False, blank=False)
    vectorized = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class PostStatus(models.Model):
    """
    Track post statuses, particularly deleted posts, to avoid repeated crawling attempts
    """

    STATUS_CHOICES = [
        ("DELETED", "Deleted"),
        ("ERROR", "Error"),
        ("SAVED", "Saved"),
    ]

    post_id = models.IntegerField(unique=True, null=False, blank=False)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, null=False, blank=False
    )
    last_checked = models.DateTimeField(auto_now=True)
    error_message = models.TextField(
        null=True, blank=True, help_text="Error message if any"
    )

    class Meta:
        verbose_name = "Post Status"
        verbose_name_plural = "Post Statuses"
        indexes = [
            models.Index(fields=["post_id"]),
        ]

    def __str__(self):
        return f"Post {self.post_id} - {self.get_status_display()}"


class AllowedCategory(models.Model):
    """Categories that are allowed to be collected by the crawler"""

    CATEGORY_GROUPS = [
        ("창플지기_칼럼", "창플지기 칼럼"),
        ("창플_이야기", "창플 이야기"),
        ("창플_아키", "창플 아키"),
        ("창플_프랜차이즈", "창플 프랜차이즈"),
        ("창플_팀비즈니스", "창플 팀비즈니스"),
        ("창플_파트너스", "창플 파트너스"),
        ("알아두면_좋은_이야기", "알아두면 좋은 이야기"),
        ("창플_Youtube영상", "창플 Youtube영상"),
        ("창플인터뷰", "창플인터뷰"),
        ("창플지기_상담", "창플지기 상담"),
        ("처음왔어요", "처음왔어요"),
        ("창플_커뮤니티", "창플 커뮤니티"),
        ("창플카페_이용방법", "창플카페 이용방법"),
        ("기타", "기타"),
    ]

    name = models.CharField(max_length=200, unique=True, null=False, blank=False)
    category_group = models.CharField(
        max_length=50,
        choices=CATEGORY_GROUPS,
        default="기타",
        help_text="Category group for organization",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If unchecked, this category will be ignored by the crawler",
    )
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Allowed Category"
        verbose_name_plural = "Allowed Categories"
        ordering = ["category_group", "name"]

    def __str__(self):
        return self.name


class AllowedAuthor(models.Model):
    """Allowed authors for vectorization"""

    AUTHOR_GROUPS = [
        ("창플", "창플"),
        ("팀비즈니스_브랜드_대표", "팀비즈니스 브랜드 대표"),
        ("기타", "기타"),
    ]

    name = models.CharField(max_length=200, unique=True, null=False, blank=False)
    author_group = models.CharField(
        max_length=50,
        choices=AUTHOR_GROUPS,
        default="창플",
        help_text="Author group for organization",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If unchecked, this author's posts will not be vectorized",
    )
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Allowed Author"
        verbose_name_plural = "Allowed Authors"
        ordering = ["author_group", "name"]

    def __str__(self):
        return self.name