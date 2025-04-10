# reset_keywords.py
import os

import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Import your model
from scraper.models import NaverCafeData

# Update all records to set keywords to None
updated_count = NaverCafeData.objects.all().update(keywords=None)

print(f"Successfully reset keywords to null for {updated_count} records.")
