# Naver Cafe Scraper

This module contains a web scraper for collecting data from Naver Cafe.

## Features

- Class-based architecture for better code organization
- Efficient database checking to avoid redundant requests
- Batch saving to prevent data loss during unexpected crashes
- Tracking of deleted/inaccessible posts to avoid repeated attempts
- Support for category filtering
- Customizable crawling ranges with start and end IDs

## Category Management

The scraper can be configured to only collect posts from specific categories. Categories are managed through the Django admin panel.

### Loading Categories

To load all available categories from the Naver Cafe sidebar:

```bash
python manage.py load_categories
```

This will add any missing categories to the database without affecting existing ones.

To reset all categories and start fresh:

```bash
python manage.py load_categories --reset
```

### Managing Categories in Admin Panel

1. Go to the Django admin panel
2. Navigate to "Allowed Categories"
3. You can:
   - Filter categories by group
   - Toggle active status directly from the list view
   - Use bulk actions to activate/deactivate multiple categories at once
   - Search for specific categories by name

Only categories marked as "active" will be collected by the scraper.

## Post Status Tracking

The scraper maintains a record of posts that are deleted, inaccessible, or result in errors. This prevents the crawler from repeatedly attempting to access posts that don't exist or can't be accessed.

### Managing Post Statuses in Admin Panel

1. Go to the Django admin panel
2. Navigate to "Post Statuses"
3. You can:
   - View all posts that have been marked as deleted/not found
   - Filter by status type (DELETED, NOT_FOUND, ACCESS_DENIED, ERROR)
   - Delete status entries if you want to retry scraping those posts
   - See when each post was last checked and any error messages

## Handling Migrations

If you need to reset migrations:

1. Delete all migration files in `scraper/migrations/` except for `__init__.py`
2. Run `python manage.py makemigrations`
3. Run `python manage.py migrate --fake-initial`
4. Load the categories: `python manage.py load_categories`

This approach separates the data loading from the migrations, making it easier to manage changes to the database schema.

## Running the Scraper

### Using the Management Command

The easiest way to run the scraper is using the management command:

```bash
python manage.py run_crawler
```

This will automatically:
1. Find the latest post ID in the database
2. Determine the latest post ID from the Naver Cafe
3. Collect all posts in between that match your active categories

#### Command Options

You can customize the crawler behavior with these options:

```bash
# Specify a starting post ID (overrides the last post in database)
python manage.py run_crawler --start-id=51000

# Specify an ending post ID
python manage.py run_crawler --end-id=51153

# Specify both start and end IDs to collect a specific range
python manage.py run_crawler --start-id=51000 --end-id=51153

# Enable debug logging
python manage.py run_crawler --debug
```

### Using Python Shell

You can also run the crawler from the Python shell:

```bash
python manage.py shell
```

```python
import asyncio
from scraper.services.crawler import main

# Run with default settings
asyncio.run(main())

# Run with custom parameters
asyncio.run(main(
    start_id=51000,
    end_id=51153
))
```

## Optimizations

The scraper includes several optimizations to improve efficiency:

### Database Checking

Before attempting to scrape a post, the crawler checks if:
1. The post already exists in the database
2. The post has been previously marked as deleted/inaccessible

This avoids making unnecessary network requests for content we already have or know isn't accessible.

### Batch Saving

Data is saved to the database in batches (every 100 posts by default) to:
1. Reduce database transactions
2. Prevent data loss if the process terminates unexpectedly
3. Maintain performance with larger datasets

### Error Handling

The crawler automatically tracks deleted posts and posts with errors:
1. Posts that redirect to the main page are marked as deleted
2. Posts that show error messages are tracked with their specific error
3. Posts that fail to load or extract content are marked appropriately

Future crawling runs will skip these posts unless their status entries are manually deleted in the admin panel.

The scraper will only collect posts from categories that are marked as active in the database. 