# Naver Cafe Scraper

This module contains a web scraper for collecting data from Naver Cafe.

## Features

- Class-based architecture for better code organization
- Efficient database checking to avoid redundant requests
- Batch saving to prevent data loss during unexpected crashes
- Tracking of deleted/inaccessible posts to avoid repeated attempts
- Support for category filtering
- Customizable crawling ranges with start and end IDs
- Scheduled scraping with Redis and RQ

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

The easiest way to run the scraper manually is using the management command:

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

## Scheduled Scraping

The scraper can be scheduled to run automatically using Redis and RQ:

### Prerequisites

1. Install Redis on your server or use a hosted Redis service
2. Ensure the Redis service is running
3. Configure the Redis connection in `settings.py` if needed

### Setting Up Scheduled Scraping

To schedule the crawler to run daily at a specific time (all times are in UTC):

```bash
# Schedule to run daily at 3:00 AM UTC
python manage.py schedule_crawler start --hour=3 --minute=0

# Schedule to run daily at 12:30 PM UTC
python manage.py schedule_crawler start --hour=12 --minute=30
```

### Managing Scheduled Jobs

You can view and manage scheduled jobs using the following commands:

```bash
# List all scheduled jobs
python manage.py schedule_crawler list

# Cancel all scheduled jobs
python manage.py schedule_crawler cancel

# Schedule a custom job with specific parameters
python manage.py schedule_crawler custom --start-id=51000 --end-id=51200

# Run a custom job immediately (doesn't wait for scheduler)
python manage.py schedule_crawler custom --start-id=51000 --end-id=51200 --now

# Check the current status of the queue
python manage.py schedule_crawler status
```

### Running the Worker

For the scheduled jobs to run, you need to have at least one RQ worker running:

```bash
python manage.py rqworker default
```

For production use, consider using a process manager like Supervisor to keep the worker running.

### RQ Dashboard

Django RQ provides a dashboard to monitor jobs. Access it at:

```
http://your-server/django-rq/
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

## Relationship Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Django Application                             │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                ┌─────────────────────────────────────────┐
                │                                         │
                ▼                                         ▼
┌────────────────────────────┐            ┌───────────────────────────────┐
│   Management Commands      │            │      Scraper Services         │
│                            │            │                               │
│ schedule_crawler.py        │◄───────┐   │ scheduler.py                  │
│  - daily                   │        │   │  - schedule_daily_crawler()   │
│  - custom                  │        │   │  - schedule_custom_crawler()  │
│  - status                  │        │   │  - get_scheduler()            │
│  - list                    │        │   │  - list_scheduled_jobs()      │
│  - cancel                  │        │   │                               │
└────────────┬───────────────┘        │   │ crawler.py                    │
             │                        │   │  - NaverCafeScraper           │
             └────────────────────────┼───┼─► - scrape_posts()            │
                                      │   │  - scrape_post()              │
                                      │   └───────────────┬───────────────┘
                                      │                   │
                                      │                   │
                                      │                   ▼
┌─────────────────────────────────────┴─┐       ┌─────────────────────────┐
│                                        │       │   Database Models       │
│      Redis + RQ Infrastructure         │       │                         │
│                                        │       │ - Post                  │
│ ┌────────────────┐  ┌────────────────┐ │       │ - PostStatus           │
│ │   RQ Queues    │  │  RQ Scheduler  │ │       │ - Other models...      │
│ │                │◄─┤                │ │       └────────────┬────────────┘
│ │ - default      │  │ - Schedule jobs│ │                    │
│ │ - failed       │  │ - Cron jobs    │ │                    │
│ └───────┬────────┘  └────────────────┘ │                    │
│         │                              │                    │
└─────────┼──────────────────────────────┘                    │
          │                                                   │
          ▼                                                   ▼
┌─────────────────────┐                           ┌─────────────────────────┐
│    Worker Processes │                           │                         │
│                     │                           │      Naver Cafe         │
│ - rqworker          │◄────Scrapes data─────────┼─────► (External site)    │
│ - rqscheduler       │                           │                         │
└─────────────────────┘                           └─────────────────────────┘
```

## Data Flow

1. **User Interaction**: Users interact via Django management commands (`schedule_crawler.py`), which can schedule jobs, check status, list jobs, or cancel them.

2. **Job Scheduling**:
   - `schedule_crawler.py` calls functions in `scheduler.py`
   - `scheduler.py` uses RQ Scheduler to schedule jobs for future execution
   - Scheduled jobs are stored in Redis

3. **Job Execution Flow**:
   - `rqscheduler` worker monitors scheduled jobs
   - When a job is due, it's moved to the RQ queue
   - `rqworker` processes pick up jobs from the queue
   - Workers execute `run_scheduled_crawler` in `tasks.py`
   - The task creates a `NaverCafeScraper` instance and calls its methods
   - The scraper retrieves data from Naver Cafe
   - Scraped data is saved to Django models

4. **Core Components**:
   - **NaverCafeScraper**: Handles the web scraping logic
   - **Redis**: Stores job queues and scheduled jobs
   - **RQ Workers**: Process jobs from queues
   - **RQ Scheduler**: Moves scheduled jobs to the queue at the right time
   - **Django Models**: Store scraped data

This architecture separates concerns between scheduling, job management, scraping logic, and data storage, allowing for a maintainable and scalable system.

## Running Workers

To ensure scheduled jobs execute properly, you need to run both:

1. **RQ Worker** - processes jobs from the queue:
   ```
   python manage.py rqworker default
   ```

2. **RQ Scheduler Worker** - moves scheduled jobs to the queue when due:
   ```
   python manage.py rqscheduler
   ```

Both processes must be running simultaneously for the scheduled scraping to work correctly.

For more detailed information about the scraper functionality, see the [scraper module README](z_docs/scrpaer_guide.md).