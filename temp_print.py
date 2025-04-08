import os
import sys

import django

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db.models import Q
from django.db.models.functions import Length

from scraper.models import NaverCafeData

# Query posts from allowed authors and categories with content length > min_content_length
# Use proper Length annotation instead of unsupported len lookup
posts = (
    NaverCafeData.objects.annotate(content_length=Length("content"))
    .filter(
        author__in=["창플"],
        content_length__gt=100,
    )
    .filter(Q(notation=None) | Q(keywords=None))
)

print(f"Posts matching filter criteria: {posts.count()}")
for post in posts[:5]:  # Only print first 5 to avoid flooding console
    print(f"Post ID: {post.post_id}, Has notation: {post.notation is not None}")

# Print posts with notation (to verify data was added correctly)
print("\n--- Posts with notation values ---")
posts_with_notation = NaverCafeData.objects.exclude(notation=None)[
    :10
]  # Get first 10 for sample
print(
    f"Found {posts_with_notation.count()} posts with notation values (showing first 10)"
)

for post in posts_with_notation:
    print(f"\nPost ID: {post.post_id}")
    print(f"Title: {post.title[:50]}...")
    print(f"Notation type: {type(post.notation)}")

    # If notation is a list, print length and sample of first item
    if isinstance(post.notation, list):
        print(post.notation)
    else:
        print(f"Notation sample: {str(post.notation)[:100]}...")

# Stats on posts without notation
posts_without_notation = NaverCafeData.objects.filter(notation=None).count()
print(f"\n--- Statistics ---")
print(f"Total posts: {NaverCafeData.objects.count()}")
print(f"Posts with notation: {NaverCafeData.objects.exclude(notation=None).count()}")
print(f"Posts without notation: {posts_without_notation}")
print("----------------------")
