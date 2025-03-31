import logging
import os
from collections import defaultdict

from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from pinecone import Pinecone
from tqdm import tqdm

load_dotenv()

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Find and delete duplicate vectors in Pinecone by comparing metadata content"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report duplicates without deleting them",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting duplicate vector detection..."))

        PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
        PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME")

        if not PINECONE_API_KEY or not PINECONE_INDEX_NAME:
            self.stdout.write(
                self.style.ERROR(
                    "Pinecone API key or index name not found in environment variables"
                )
            )
            return

        # Initialize Pinecone
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(PINECONE_INDEX_NAME)

        # Get index stats
        stats = index.describe_index_stats()
        total_vectors = stats.total_vector_count
        self.stdout.write(
            self.style.SUCCESS(f"Total vectors in index: {total_vectors}")
        )

        # We'll fetch vectors in batches
        BATCH_SIZE = 1000
        next_pagination_token = None

        # Track duplicates by post_id AND content
        # Using a tuple of (post_id, content) as the key
        content_vectors = defaultdict(list)
        duplicate_ids = []

        self.stdout.write(
            self.style.SUCCESS("Fetching vectors and checking for duplicates...")
        )

        # Paginate through all vectors
        with tqdm(total=total_vectors) as pbar:
            while True:
                # Fetch vectors
                query_response = index.query(
                    vector=[0] * 3072,  # Dummy vector for fetching
                    top_k=BATCH_SIZE,
                    include_metadata=True,
                    include_values=False,
                    pagination_token=next_pagination_token,
                )

                # Process each vector
                for match in query_response.matches:
                    if not match.metadata or "post_id" not in match.metadata:
                        continue

                    post_id = match.metadata.get("post_id")
                    content = match.metadata.get("text", "")

                    # Generate a key based on both post_id and full content
                    # This ensures we only consider exact content duplicates
                    vector_key = (post_id, content)

                    # Add to our tracking dictionary
                    content_vectors[vector_key].append(
                        {
                            "id": match.id,
                            "post_id": post_id,
                            # Store creation timestamp if available to keep the newest
                            "timestamp": match.metadata.get("timestamp", ""),
                        }
                    )

                # Update progress
                pbar.update(len(query_response.matches))

                # Check if we need to continue pagination
                next_pagination_token = query_response.pagination_token
                if (
                    not next_pagination_token
                    or len(query_response.matches) < BATCH_SIZE
                ):
                    break

        # Find duplicates
        self.stdout.write(self.style.SUCCESS("Analyzing vectors to find duplicates..."))
        duplicate_count = 0

        for (post_id, content), vectors in content_vectors.items():
            if len(vectors) > 1:
                # Keep the first vector, mark the rest as duplicates
                duplicate_count += len(vectors) - 1

                # Log details about the duplicates we found
                self.stdout.write(
                    f"Found {len(vectors)} duplicates for post_id={post_id}, content starts with: {content[:50]}..."
                )

                for vec in vectors[1:]:
                    duplicate_ids.append(vec["id"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Found {len(duplicate_ids)} duplicate vectors across {duplicate_count} entries"
            )
        )

        # Delete duplicates if not dry run
        if duplicate_ids and not options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleting {len(duplicate_ids)} duplicate vectors..."
                )
            )

            # Delete in batches to avoid overwhelming the API
            DELETION_BATCH_SIZE = 100
            for i in range(0, len(duplicate_ids), DELETION_BATCH_SIZE):
                batch = duplicate_ids[i : i + DELETION_BATCH_SIZE]
                index.delete(ids=batch)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Deleted batch {i//DELETION_BATCH_SIZE + 1}/{(len(duplicate_ids) + DELETION_BATCH_SIZE - 1)//DELETION_BATCH_SIZE}"
                    )
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {len(duplicate_ids)} duplicate vectors"
                )
            )
        elif options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS("Dry run completed. No vectors were deleted.")
            )

        # Get updated stats
        stats = index.describe_index_stats()
        self.stdout.write(
            self.style.SUCCESS(
                f"Total vectors in index after cleanup: {stats.total_vector_count}"
            )
        )
