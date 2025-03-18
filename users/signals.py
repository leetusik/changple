from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import NaverUserProfile


@receiver(post_save, sender=NaverUserProfile)
def check_premium_status(sender, instance, created, **kwargs):
    """
    Signal to check if a user's premium status has expired and update accordingly
    """
    if not created and instance.is_premium:
        if instance.premium_until and instance.premium_until < timezone.now():
            instance.is_premium = False
            instance.save(update_fields=["is_premium"])
