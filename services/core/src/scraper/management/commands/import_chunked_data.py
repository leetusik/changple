"""
Import chunked NaverCafeData and PostStatus data from backup directory.

Adapted from changple2's export/import commands for changple3 deployment.
"""

import glob
import json
import os

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_datetime

from src.scraper.models import AllowedAuthor, GoodtoKnowBrands, NaverCafeData, PostStatus


class Command(BaseCommand):
    help = "Import chunked NaverCafeData and PostStatus data from backup directory"

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            type=str,
            default="/app/z_docs/data/z_data",
            help="Data directory containing chunked JSON files",
        )
        parser.add_argument(
            "--manifest-file",
            type=str,
            help="Path to specific manifest file (auto-detects if not provided)",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Update existing records instead of skipping them",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing data before importing (DANGEROUS!)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Batch size for bulk operations (default: 1000)",
        )
        parser.add_argument(
            "--skip-navercafe",
            action="store_true",
            help="Skip NaverCafeData import",
        )

    def handle(self, *args, **options):
        data_dir = options["data_dir"]
        manifest_file = options["manifest_file"]
        update_existing = options["update_existing"]
        clear_existing = options["clear_existing"]
        batch_size = options["batch_size"]
        skip_navercafe = options["skip_navercafe"]

        if not os.path.exists(data_dir):
            self.stdout.write(self.style.ERROR(f"Data directory not found: {data_dir}"))
            return

        manifest_path = self._find_manifest_file(data_dir, manifest_file)
        if not manifest_path:
            self.stdout.write(self.style.ERROR("No manifest file found."))
            return

        manifest = self._load_manifest(manifest_path)
        if not manifest:
            return

        self._print_import_info(manifest)

        if clear_existing:
            self._clear_existing_data()

        try:
            # Import supporting models first
            self._import_supporting_models(data_dir, manifest)

            # Import NaverCafeData
            if not skip_navercafe:
                self._import_navercafe_data_chunked(data_dir, manifest, update_existing, batch_size)

            # Import PostStatus
            self._import_poststatus_data(data_dir, manifest, update_existing, batch_size)

            self.stdout.write(self.style.SUCCESS("Import completed successfully!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Import failed: {e}"))
            raise

    def _find_manifest_file(self, data_dir, manifest_file):
        if manifest_file:
            if os.path.exists(manifest_file):
                return manifest_file
            self.stdout.write(self.style.ERROR(f"Manifest not found: {manifest_file}"))
            return None

        manifest_pattern = os.path.join(data_dir, "export_manifest_*.json")
        manifest_files = glob.glob(manifest_pattern)

        if not manifest_files:
            self.stdout.write(self.style.ERROR(f"No manifest files in {data_dir}"))
            return None

        latest_manifest = max(manifest_files, key=os.path.getctime)
        self.stdout.write(f"Using manifest: {os.path.basename(latest_manifest)}")
        return latest_manifest

    def _load_manifest(self, manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            required_keys = ["export_timestamp", "datasets"]
            for key in required_keys:
                if key not in manifest:
                    self.stdout.write(self.style.ERROR(f"Invalid manifest: missing '{key}'"))
                    return None

            return manifest
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading manifest: {e}"))
            return None

    def _print_import_info(self, manifest):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("IMPORT INFORMATION")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Export timestamp: {manifest['export_timestamp']}")

        datasets = manifest.get("datasets", {})

        navercafe_data = datasets.get("navercafe_data", {})
        if navercafe_data.get("status") == "completed":
            self.stdout.write(
                f"NaverCafeData: {navercafe_data['total_records']:,} records "
                f"in {navercafe_data['total_chunks']} chunks"
            )

        post_status = datasets.get("post_status", {})
        if post_status.get("status") == "completed":
            self.stdout.write(f"PostStatus: {post_status['total_records']:,} records")

        supporting = datasets.get("supporting_models", {})
        if supporting.get("status") == "completed":
            for file_info in supporting["files"]:
                self.stdout.write(f"{file_info['model']}: {file_info['records_count']} records")

        self.stdout.write("=" * 60 + "\n")

    def _clear_existing_data(self):
        with transaction.atomic():
            counts = {
                "NaverCafeData": NaverCafeData.objects.count(),
                "PostStatus": PostStatus.objects.count(),
                "AllowedAuthor": AllowedAuthor.objects.count(),
                "GoodtoKnowBrands": GoodtoKnowBrands.objects.count(),
            }

            NaverCafeData.objects.all().delete()
            PostStatus.objects.all().delete()
            AllowedAuthor.objects.all().delete()
            GoodtoKnowBrands.objects.all().delete()

            self.stdout.write(
                self.style.WARNING(
                    f"Cleared: {counts['NaverCafeData']} NaverCafeData, "
                    f"{counts['PostStatus']} PostStatus, "
                    f"{counts['AllowedAuthor']} AllowedAuthor, "
                    f"{counts['GoodtoKnowBrands']} GoodtoKnowBrands"
                )
            )

    def _import_supporting_models(self, data_dir, manifest):
        self.stdout.write("Importing supporting models...")

        supporting = manifest.get("datasets", {}).get("supporting_models", {})
        if supporting.get("status") != "completed":
            return

        for file_info in supporting["files"]:
            model_name = file_info["model"]
            filename = file_info["filename"]
            filepath = os.path.join(data_dir, filename)

            if not os.path.exists(filepath):
                self.stdout.write(self.style.WARNING(f"File not found: {filename}"))
                continue

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if model_name == "AllowedAuthor":
                self._import_allowed_authors(data)
            elif model_name == "GoodtoKnowBrands":
                self._import_goodto_know_brands(data)

    def _import_allowed_authors(self, data):
        created, updated = 0, 0
        with transaction.atomic():
            for item in data:
                obj, was_created = AllowedAuthor.objects.update_or_create(
                    name=item["name"],
                    defaults={
                        "author_group": item["author_group"],
                        "is_active": item["is_active"],
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
        self.stdout.write(f"  AllowedAuthor: {created} created, {updated} updated")

    def _import_goodto_know_brands(self, data):
        created, updated = 0, 0
        with transaction.atomic():
            for item in data:
                obj, was_created = GoodtoKnowBrands.objects.update_or_create(
                    name=item["name"],
                    defaults={
                        "description": item.get("description"),
                        "is_goodto_know": item.get("is_goodto_know", True),
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
        self.stdout.write(f"  GoodtoKnowBrands: {created} created, {updated} updated")

    def _import_navercafe_data_chunked(self, data_dir, manifest, update_existing, batch_size):
        self.stdout.write("Importing NaverCafeData chunks...")

        navercafe_data = manifest.get("datasets", {}).get("navercafe_data", {})
        if navercafe_data.get("status") != "completed":
            return

        chunks = navercafe_data.get("chunks", [])
        totals = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

        for i, chunk_info in enumerate(chunks):
            filename = chunk_info["filename"]
            filepath = os.path.join(data_dir, filename)

            if not os.path.exists(filepath):
                self.stdout.write(self.style.WARNING(f"Chunk not found: {filename}"))
                continue

            self.stdout.write(
                f"Processing chunk {i+1}/{len(chunks)}: {filename} "
                f"({chunk_info['records_count']} records)"
            )

            with open(filepath, "r", encoding="utf-8") as f:
                chunk_data = json.load(f)

            created, updated, skipped, errors = self._import_navercafe_chunk(
                chunk_data, update_existing, batch_size
            )

            totals["created"] += created
            totals["updated"] += updated
            totals["skipped"] += skipped
            totals["errors"] += errors

            self.stdout.write(
                f"  Chunk {i+1}: {created} created, {updated} updated, "
                f"{skipped} skipped, {errors} errors"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"NaverCafeData: {totals['created']} created, {totals['updated']} updated, "
                f"{totals['skipped']} skipped, {totals['errors']} errors"
            )
        )

    def _import_navercafe_chunk(self, chunk_data, update_existing, batch_size):
        created, updated, skipped, errors = 0, 0, 0, 0

        for i in range(0, len(chunk_data), batch_size):
            batch = chunk_data[i : i + batch_size]

            with transaction.atomic():
                for item in batch:
                    try:
                        published_date = parse_datetime(item["published_date"])
                        created_at = parse_datetime(item["created_at"])
                        updated_at = parse_datetime(item["updated_at"])

                        defaults = {
                            "title": item["title"],
                            "category": item["category"],
                            "content": item["content"],
                            "author": item["author"],
                            "published_date": published_date,
                            "notation": item.get("notation"),
                            "keywords": item.get("keywords"),
                            "summary": item.get("summary"),
                            "possible_questions": item.get("possible_questions"),
                            "ingested": item.get("ingested", False),
                            "created_at": created_at,
                            "updated_at": updated_at,
                        }

                        if update_existing:
                            obj, was_created = NaverCafeData.objects.update_or_create(
                                post_id=item["post_id"], defaults=defaults
                            )
                            if was_created:
                                created += 1
                            else:
                                updated += 1
                        else:
                            if not NaverCafeData.objects.filter(post_id=item["post_id"]).exists():
                                NaverCafeData.objects.create(post_id=item["post_id"], **defaults)
                                created += 1
                            else:
                                skipped += 1

                    except Exception:
                        errors += 1

        return created, updated, skipped, errors

    def _import_poststatus_data(self, data_dir, manifest, update_existing, batch_size):
        self.stdout.write("Importing PostStatus data...")

        post_status = manifest.get("datasets", {}).get("post_status", {})
        if post_status.get("status") != "completed":
            return

        filename = post_status["filename"]
        filepath = os.path.join(data_dir, filename)

        if not os.path.exists(filepath):
            self.stdout.write(self.style.WARNING(f"PostStatus file not found: {filename}"))
            return

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        created, updated, skipped, errors = 0, 0, 0, 0

        for i in range(0, len(data), batch_size):
            batch = data[i : i + batch_size]

            with transaction.atomic():
                for item in batch:
                    try:
                        created_at = parse_datetime(item["created_at"])
                        updated_at = parse_datetime(item["updated_at"])

                        defaults = {
                            "status": item["status"],
                            "error_message": item.get("error_message"),
                            "created_at": created_at,
                            "updated_at": updated_at,
                        }

                        if update_existing:
                            obj, was_created = PostStatus.objects.update_or_create(
                                post_id=item["post_id"], defaults=defaults
                            )
                            if was_created:
                                created += 1
                            else:
                                updated += 1
                        else:
                            if not PostStatus.objects.filter(post_id=item["post_id"]).exists():
                                PostStatus.objects.create(post_id=item["post_id"], **defaults)
                                created += 1
                            else:
                                skipped += 1

                    except Exception:
                        errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"PostStatus: {created} created, {updated} updated, "
                f"{skipped} skipped, {errors} errors"
            )
        )
