import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from scraper.models import AllowedAuthor, NaverCafeData


class Command(BaseCommand):
    help = "Export posts with vectorized=False and specified authors to CSV"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Output file path (default: posts_YYYY-MM-DD.csv in project root)",
        )
        parser.add_argument(
            "--limit", type=int, default=None, help="Limit the number of posts exported"
        )

    def handle(self, *args, **options):
        # Get output path
        output_path = options["output"]
        if not output_path:
            today = timezone.now().strftime("%Y-%m-%d")
            output_path = f"posts_{today}.csv"

        # Get allowed authors
        allowed_authors = list(
            AllowedAuthor.objects.filter(is_active=True).values_list("name", flat=True)
        )

        query = NaverCafeData.objects.filter(author__in=allowed_authors)

        # Apply limit if specified
        limit = options["limit"]
        if limit:
            query = query[:limit]
            self.stdout.write(self.style.SUCCESS(f"Limiting export to {limit} posts"))

        total_posts = query.count()
        self.stdout.write(self.style.SUCCESS(f"Found {total_posts} posts to export"))

        if total_posts == 0:
            self.stdout.write(self.style.WARNING("No posts to export. Exiting."))
            return

        # Write to CSV
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "post_id",
                "title",
                "content",
                "author",
                "category",
                "published_date",
                "url",
                "vectorized",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Process in batches to avoid memory issues
            batch_size = 1000
            for i in range(0, total_posts, batch_size):
                batch = query[i : i + batch_size]
                for post in batch:
                    writer.writerow(
                        {
                            "post_id": post.post_id,
                            "title": post.title,
                            "content": post.content,
                            "author": post.author,
                            "category": post.category,
                            "published_date": post.published_date,
                            "url": post.url,
                            "vectorized": post.vectorized,
                        }
                    )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Processed {min(i+batch_size, total_posts)}/{total_posts} posts"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully exported {total_posts} posts to {output_path}"
            )
        )
