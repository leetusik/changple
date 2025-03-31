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
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Batch size for fetching vectors (default: 100)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting duplicate vector detection..."))

        PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
        PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME")
        BATCH_SIZE = options["batch_size"]

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

        # Track duplicates by post_id AND content
        # Using a tuple of (post_id, content) as the key
        content_vectors = defaultdict(list)
        duplicate_ids = []

        self.stdout.write(
            self.style.SUCCESS("Fetching vectors and checking for duplicates...")
        )

        # First, list all vector IDs
        self.stdout.write(self.style.SUCCESS("Getting all vector IDs..."))
        try:
            # Use describe_index_stats namespace to get vector IDs in each namespace
            all_vector_ids = []
            namespaces = stats.namespaces

            if not namespaces:
                # If no namespaces, use default namespace
                namespace_stats = {"": stats.total_vector_count}
            else:
                namespace_stats = {
                    ns: ns_stats.vector_count for ns, ns_stats in namespaces.items()
                }

            # Process each namespace
            for namespace, count in namespace_stats.items():
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Processing namespace '{namespace or 'default'}' with {count} vectors"
                    )
                )

                # Fetch vector IDs in batches
                vector_ids = []
                for i in range(0, count, BATCH_SIZE):
                    try:
                        # Fetch vectors from this namespace
                        fetch_response = index.fetch(
                            ids=[], namespace=namespace, limit=BATCH_SIZE, offset=i
                        )
                        # Add IDs to our list
                        if fetch_response and fetch_response.vectors:
                            batch_ids = list(fetch_response.vectors.keys())
                            vector_ids.extend(batch_ids)
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Fetched batch of {len(batch_ids)} vector IDs"
                                )
                            )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error fetching vectors: {e}")
                        )

                all_vector_ids.extend(vector_ids)

            self.stdout.write(
                self.style.SUCCESS(f"Retrieved {len(all_vector_ids)} vector IDs")
            )

            # Now fetch vectors in batches and check for duplicates
            with tqdm(total=len(all_vector_ids)) as pbar:
                for i in range(0, len(all_vector_ids), BATCH_SIZE):
                    batch_ids = all_vector_ids[i : i + BATCH_SIZE]

                    try:
                        # Fetch vector metadata
                        fetch_response = index.fetch(ids=batch_ids)

                        # Process each vector
                        for vec_id, vector in fetch_response.vectors.items():
                            if not vector.metadata or "post_id" not in vector.metadata:
                                continue

                            post_id = vector.metadata.get("post_id")
                            content = vector.metadata.get("text", "")

                            # Generate a key based on both post_id and full content
                            vector_key = (post_id, content)

                            # Add to our tracking dictionary
                            content_vectors[vector_key].append(
                                {
                                    "id": vec_id,
                                    "post_id": post_id,
                                    "timestamp": vector.metadata.get("timestamp", ""),
                                }
                            )

                        # Update progress
                        pbar.update(len(batch_ids))
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error processing batch: {e}")
                        )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            return

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
