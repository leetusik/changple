from django.db import models
from django.utils import timezone

# Create your models here.


class EmailLog(models.Model):
    """Model to log email sending history"""

    STATUS_CHOICES = (
        ("queued", "Queued"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    )

    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="queued")
    status_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.recipient} - {self.subject} - {self.status}"

    def mark_as_sent(self):
        self.status = "sent"
        self.sent_at = timezone.now()
        self.save()

    def mark_as_failed(self, message=None):
        self.status = "failed"
        if message:
            self.status_message = message
        self.save()
