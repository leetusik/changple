"""
Common models for Changple Core service.
"""

from django.db import models


class CommonModel(models.Model):
    """
    Abstract base model with created_at and updated_at timestamps.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
