from django.db import models


# Create your models here.
class NaverCafeData(models.Model):
    title = models.CharField(max_length=200, null=False, blank=False)
    content = models.TextField(null=False, blank=False)
    author = models.CharField(max_length=200, null=False, blank=False)
    published_date = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    url = models.URLField(unique=True, null=False, blank=False)
    post_id = models.IntegerField(null=False, blank=False)

    def __str__(self):
        return self.title
