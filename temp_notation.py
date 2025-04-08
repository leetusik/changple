import ast
import csv
import json
import os
import sys

import django

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Set up Django environment
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "config.settings"
)  # Replace 'config.settings' with your actual settings module
django.setup()

from scraper.models import NaverCafeData


def update_notations_from_csv(csv_filepath):
    """
    Updates the 'notation' field in NaverCafeData model from a CSV file.

    Args:
        csv_filepath (str): The path to the CSV file.
    """
    updated_count = 0
    not_found_count = 0
    error_count = 0
    skipped_empty_notation = 0

    try:
        with open(csv_filepath, mode="r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            if (
                "post_id" not in reader.fieldnames
                or "notation" not in reader.fieldnames
            ):
                print(f"Error: CSV file must contain 'post_id' and 'notation' columns.")
                return

            for row in reader:
                post_id_str = row.get("post_id")
                notation_list = ast.literal_eval(row.get("notation"))

                if not post_id_str:
                    print(f"Skipping row due to missing post_id: {row}")
                    error_count += 1
                    continue

                try:
                    post_id = int(post_id_str)
                except ValueError:
                    print(f"Skipping row due to invalid post_id: {post_id_str}")
                    error_count += 1
                    continue

                try:
                    post_data = NaverCafeData.objects.get(post_id=post_id)
                    post_data.notation = notation_list
                    post_data.save()
                    updated_count += 1
                    # print(f"Successfully updated notation for post_id {post_id}")
                except NaverCafeData.DoesNotExist:
                    # print(f"Post with post_id {post_id} not found in the database.")
                    not_found_count += 1
                except Exception as e:
                    print(f"Error updating post_id {post_id}: {e}")
                    error_count += 1

    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_filepath}")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return

    print(f"--- Update Summary ---")
    print(f"Successfully updated: {updated_count}")
    print(f"Skipped (empty notation): {skipped_empty_notation}")
    print(f"Post IDs not found in DB: {not_found_count}")
    print(f"Errors during processing: {error_count}")
    print(f"----------------------")


if __name__ == "__main__":
    csv_file = (
        "navercafe_essays_bum9_evaluated.csv"  # Assumes the CSV is in the project root
    )
    print(f"Starting notation update from {csv_file}...")
    update_notations_from_csv(csv_file)
    print("Notation update process finished.")
