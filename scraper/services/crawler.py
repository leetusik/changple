import asyncio
import logging
import os
import random
import re
import traceback
from typing import Any, Dict, List, Optional, Tuple

import dotenv
from asgiref.sync import sync_to_async
from django.db import transaction
from pinecone import Pinecone
from playwright.async_api import Browser, BrowserContext, ElementHandle, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from scraper.models import AllowedCategory, NaverCafeData, PostStatus

dotenv.load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("naver_cafe_scraper.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class NaverCafeScraper:
    """Class to scrape Naver Cafe posts"""

    def __init__(self, cafe_url: str):
        """
        Initialize the NaverCafeScraper

        Args:
            cafe_url: Base URL of the cafe to scrape
        """
        self.cafe_url = cafe_url
        self.playwright = None
        self.browser = None
        self.page = None

        # Configuration parameters
        self.config = {
            "navigation": {
                "max_retries": 3,
                "timeout": 10000,
                "page_load_timeout": 3000,
            },
            "login": {
                "retry_direct_url": "https://nid.naver.com/nidlogin.login",
                "login_wait_time": 10,
            },
        }

    async def setup(self) -> bool:
        """
        Set up the browser and page for scraping

        Returns:
            bool: True if setup was successful, False otherwise
        """
        try:
            self.playwright = await async_playwright().start()
            # self.browser = await self.playwright.chromium.launch(headless=False)
            self.browser = await self.playwright.chromium.launch(headless=True)
            context = await self.browser.new_context()
            self.page = await context.new_page()
            return True
        except Exception as e:
            logger.error(f"Error during setup: {e}")
            logger.debug(traceback.format_exc())
            await self.cleanup()
            return False

    async def cleanup(self) -> None:
        """Clean up browser resources"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            logger.debug(traceback.format_exc())

    async def navigate_with_retry(self, url: str) -> bool:
        """
        Navigate to a URL with retry logic for handling timeouts

        Args:
            url: URL to navigate to

        Returns:
            bool: True if navigation was successful, False otherwise
        """
        config = self.config["navigation"]
        max_retries = config["max_retries"]
        timeout = config["timeout"]
        page_load_timeout = config["page_load_timeout"]

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Navigation attempt {attempt}/{max_retries} to {url}")
                await self.page.goto(url, timeout=timeout)
                # Wait for the page to stabilize
                await self.page.wait_for_load_state(
                    "domcontentloaded", timeout=page_load_timeout
                )
                await self.page.wait_for_load_state(
                    "networkidle", timeout=page_load_timeout
                )
                return True
            except PlaywrightTimeoutError:
                logger.warning(
                    f"Timeout on attempt {attempt}/{max_retries} navigating to {url}"
                )
                if attempt < max_retries:
                    # Wait before retrying (increasing backoff)
                    wait_time = 3 * attempt  # 3, 6, 9 seconds...
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Failed to navigate to {url} after {max_retries} attempts"
                    )
                    return False
            except Exception as e:
                logger.error(f"Error navigating to {url}: {e}")
                return False
        return False

    async def login(self) -> bool:
        """
        Log in to Naver using credentials from .env file

        Returns:
            bool: True if login was successful, False otherwise
        """
        try:
            # Get credentials from environment variables
            naver_id = os.getenv("NAVER_ID")
            naver_pw = os.getenv("NAVER_PW")

            if not naver_id or not naver_pw:
                logger.error("Naver credentials not found in .env file")
                return False

            logger.info("Attempting to log in to Naver automatically")

            # Check if we're already on the login page, if not click the login button
            if "nid.naver.com" not in self.page.url:
                # Find and click the login button
                login_button = await self.page.query_selector(".gnb_btn_login")
                if login_button:
                    # Add a small random delay before clicking (like a human would)
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    await login_button.click()
                    # Wait for navigation to login page
                    await self.page.wait_for_load_state("networkidle")
                else:
                    logger.warning(
                        "Login button not found, trying to navigate directly to login page"
                    )
                    if not await self.navigate_with_retry(
                        self.config["login"]["retry_direct_url"]
                    ):
                        return False

            # Wait for the login form to be visible
            await self.page.wait_for_selector("#id", timeout=10000)

            # Random delay before starting to type (like a human would pause)
            await asyncio.sleep(random.uniform(0.8, 2.0))

            # Clear the fields first (sometimes auto-filled)
            await self.page.click("#id")
            await self.page.keyboard.press("Control+A")
            await self.page.keyboard.press("Delete")

            # Type ID with human-like delays between keystrokes
            for char in naver_id:
                await self.page.type("#id", char, delay=random.uniform(50, 150))
                # Occasionally add a longer pause as if thinking
                if random.random() < 0.2:
                    await asyncio.sleep(random.uniform(0.1, 0.3))

            # Random delay before moving to password field (like a human would)
            await asyncio.sleep(random.uniform(0.5, 1.2))

            # Click on password field
            await self.page.click("#pw")

            # Type password with human-like delays
            for char in naver_pw:
                await self.page.type("#pw", char, delay=random.uniform(70, 170))
                # Occasionally add a longer pause
                if random.random() < 0.2:
                    await asyncio.sleep(random.uniform(0.1, 0.3))

            # Random delay before clicking login button (like a human would)
            await asyncio.sleep(random.uniform(0.7, 1.5))

            # Click the login button
            await self.page.click(".btn_login")

            # Wait for navigation after login - increase timeout and wait for multiple load states
            await self.page.wait_for_load_state("networkidle", timeout=30000)
            await self.page.wait_for_load_state("domcontentloaded", timeout=30000)

            # Give extra time for the page to fully load and process the login
            await asyncio.sleep(5)

            # Better login success detection
            if "cafe.naver.com" in self.page.url or (
                "naver.com" in self.page.url
                and "nid.naver.com/nidlogin" not in self.page.url
            ):
                logger.info("Login successful")
                return True

            # Check for login error messages
            error_msg = await self.page.query_selector(".error_message")
            if error_msg:
                error_text = await error_msg.text_content()
                logger.error(f"Login failed: {error_text}")
                return False

            # If we can find elements that indicate we're logged in
            if await self.page.query_selector(
                ".gnb_my_li"
            ) or await self.page.query_selector(".gnb_name"):
                logger.info("Login successful based on UI elements")
                return True

            logger.warning("Login status unclear - proceeding with caution")
            return True

        except Exception as e:
            logger.error(f"Error during login: {e}")
            logger.debug(traceback.format_exc())
            return False

    async def get_latest_post_id(self) -> Optional[int]:
        """
        Get the latest post ID from the cafe main page

        Returns:
            int: Latest post ID or None if not found
        """
        try:
            logger.info("Attempting to get latest post ID from cafe main page")

            # Navigate to the main article list page
            list_url = f"{self.cafe_url}?iframe_url=/ArticleList.nhn%3Fsearch.clubid=29268355%26search.boardtype=L"
            if not await self.navigate_with_retry(list_url):
                logger.error(f"Failed to navigate to article list page: {list_url}")
                return None

            # Wait for the iframe to load
            await self.page.wait_for_selector("#cafe_main", timeout=10000)

            # Get the iframe
            iframe_element = await self.page.query_selector("#cafe_main")
            if not iframe_element:
                logger.error("Could not find iframe #cafe_main on article list page")
                return None

            # Get the frame from the iframe element
            frame = await iframe_element.content_frame()
            if not frame:
                logger.error("Could not get content frame on article list page")
                return None

            # Wait for the article list to load - specifically targeting the article-board without an ID
            await frame.wait_for_selector(
                "div.article-board.m-tcol-c:not([id])", timeout=10000
            )

            # Find the first article link within the article-board div without an ID
            article_link = await frame.query_selector(
                "div.article-board.m-tcol-c:not([id]) .board-list a.article"
            )
            if not article_link:
                logger.error(
                    "Could not find any article links in the main article list"
                )
                return None

            # Get the href attribute which contains the post ID
            href = await article_link.get_attribute("href")
            if not href:
                logger.error("Article link does not have href attribute")
                return None

            # Extract the post ID from the href
            # The href format is typically: /ArticleRead.nhn?clubid=29268355&page=1&boardtype=L&articleid=51153&referrerAllArticles=true
            match = re.search(r"articleid=(\d+)", href)
            if not match:
                logger.error(f"Could not extract post ID from href: {href}")
                return None

            post_id = int(match.group(1))
            logger.info(f"Found latest post ID: {post_id}")
            return post_id

        except Exception as e:
            logger.error(f"Error getting latest post ID: {e}")
            logger.debug(traceback.format_exc())
            return None

    @staticmethod
    @sync_to_async
    def _should_skip_post(post_id: int) -> bool:
        """
        Check if a post should be skipped (already saved or deleted)

        Args:
            post_id: The post ID to check

        Returns:
            bool: True if post should be skipped, False otherwise
        """
        try:
            with transaction.atomic():
                # Skip posts that are marked as DELETED
                if PostStatus.objects.filter(
                    post_id=post_id, status="DELETED"
                ).exists():
                    return True

                # Check if post is SAVED but has NULL published_date
                if PostStatus.objects.filter(post_id=post_id, status="SAVED").exists():
                    # Check if this post exists in NaverCafeData with a NULL published_date
                    post_with_null_date = NaverCafeData.objects.filter(
                        post_id=post_id, published_date__isnull=True
                    ).exists()

                    # If it has a NULL date, don't skip it (return False) to re-scrape it
                    # If it has a valid date, skip it (return True)
                    return not post_with_null_date

                # Don't skip posts marked as ERROR
                return False
        except Exception as e:
            logger.error(f"Error checking if post {post_id} should be skipped: {e}")
            return False

    @staticmethod
    @sync_to_async
    def _mark_post_as_deleted(
        post_id: int, error_message: Optional[str] = None
    ) -> None:
        """
        Mark a post as deleted in the PostStatus table

        Args:
            post_id: The post ID to mark
            status: Status code (DELETED, ERROR, SAVED)
            error_message: Optional error message
        """
        try:
            with transaction.atomic():
                PostStatus.objects.update_or_create(
                    post_id=post_id,
                    defaults={
                        "status": "DELETED",
                        "error_message": error_message,
                    },
                )
                logger.info(f"Marked post {post_id} as DELETED")
        except Exception as e:
            logger.error(f"Error marking post {post_id} as DELETED: {e}")

    @staticmethod
    @sync_to_async
    def _mark_post_as_saved(post_id: int) -> None:
        """
        Mark a post as saved in the PostStatus table

        Args:
            post_id: The post ID to mark
        """
        try:
            with transaction.atomic():
                PostStatus.objects.update_or_create(
                    post_id=post_id,
                    defaults={
                        "status": "SAVED",
                        "error_message": None,
                    },
                )
                logger.info(f"Marked post {post_id} as SAVED")
        except Exception as e:
            logger.error(f"Error marking post {post_id} as SAVED: {e}")

    @staticmethod
    @sync_to_async
    def _mark_post_as_error(post_id: int, error_message: str) -> None:
        """
        Mark a post as error in the PostStatus table

        Args:
            post_id: The post ID to mark
        """
        try:
            with transaction.atomic():
                PostStatus.objects.update_or_create(
                    post_id=post_id,
                    defaults={
                        "status": "ERROR",
                        "error_message": error_message,
                    },
                )
                logger.info(f"Marked post {post_id} as ERROR: {error_message}")
        except Exception as e:
            logger.error(f"Error marking post {post_id} as ERROR: {e}")

    async def scrape_post(
        self, post_id: int, allowed_categories: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Scrape a single post

        Args:
            post_id: ID of the post to scrape
            allowed_categories: List of categories to collect (if None, collect all)

        Returns:
            dict: Post data if successful, None otherwise
        """

        target_url = f"{self.cafe_url}{post_id}"
        logger.info(f"Processing post_id: {post_id}")

        if not await self.navigate_with_retry(target_url):
            logger.error(f"Failed to navigate to {target_url}")
            await self._mark_post_as_error(post_id, "Failed to navigate to URL")
            return None

        try:
            # Check if we were redirected to the base URL (indicating deleted post)
            current_url = self.page.url
            if current_url == self.cafe_url or current_url == self.cafe_url.rstrip("/"):
                logger.info(
                    f"Post {post_id} appears to be deleted (redirected to base URL)"
                )
                await self._mark_post_as_deleted(post_id, "Redirected to base URL")
                return None

            # Check for deleted post message or popup
            delete_popup = await self.page.query_selector(
                "div.error_content, div.error_area"
            )
            if delete_popup:
                msg = await delete_popup.text_content()
                logger.info(
                    f"Post {post_id} appears to be deleted or inaccessible: {msg}"
                )
                await self._mark_post_as_error(post_id, msg)
                return None

            # Wait for iframe to be available with increased timeout
            try:
                await self.page.wait_for_selector("#cafe_main", timeout=10000)
            except PlaywrightTimeoutError:
                logger.error(f"Iframe #cafe_main not found for post {post_id}")
                await self._mark_post_as_error(post_id, "Iframe #cafe_main not found")
                return None

            # Get the iframe
            iframe_element = await self.page.query_selector("#cafe_main")
            if not iframe_element:
                logger.error(f"Could not find iframe #cafe_main on page {post_id}")
                await self._mark_post_as_error(
                    post_id, "Iframe #cafe_main not found after waiting"
                )
                return None

            # Get the frame from the iframe element
            frame = await iframe_element.content_frame()
            if not frame:
                logger.error(f"Could not get content frame on page {post_id}")
                await self._mark_post_as_error(
                    post_id, "Could not get content frame from iframe"
                )
                return None

            # Simplified content loading - wait for network idle instead of multiple selectors
            await self.page.wait_for_load_state("networkidle", timeout=10000)

            # Debug selectors
            logger.info(f"Looking for content in post {post_id}")

            # Better selector handling with multiple attempts
            selectors = self._get_selectors()

            post_data = await self._extract_post_content(
                frame, selectors, post_id, target_url
            )

            if not post_data:
                await self._mark_post_as_error(post_id, "Failed to extract content")
                return None

            # No longer filter by category - keep comment for documentation
            # if allowed_categories and post_data["category"] not in allowed_categories:
            #     logger.info(
            #         f"Skipping post {post_id} with category '{post_data['category']}' (not in allowed list)"
            #     )
            #     return None

            return post_data

        except Exception as e:
            logger.error(f"Error in post_id {post_id}: {str(e)}")
            logger.debug(traceback.format_exc())
            await self._mark_post_as_deleted(post_id, str(e))
            return None

    def _get_selectors(self) -> List[Dict[str, str]]:
        """Get the selector sets for post content extraction"""
        return [
            # First attempt with specific selectors
            {
                "title": "h3.article_title",
                "content": "div.article_body",
                "author": "div.article_info a.m-tcol-c",
                "date": "div.article_info span.date",
                "category": "a.link_board, .article_head .board",
            },
            # Fallback selectors
            {
                "title": ".title_text",
                "content": ".se-main-container",
                "author": ".nick_box .nickname",
                "date": ".article_info .date",
                "category": ".article_info .board, .article_category",
            },
            # More generic selectors as last resort
            {
                "title": "h3",
                "content": "div.ContentRenderer, div.se-component-content",
                "author": "a.nickname, a.m-tcol-c",
                "date": "span.date, time",
                "category": ".board, .article_category, a[href*='menuid']",
            },
        ]

    async def _extract_post_content(
        self, frame, selectors, post_id, url
    ) -> Optional[Dict[str, Any]]:
        """
        Extract post content using different selector sets

        Args:
            frame: Playwright frame object
            selectors: List of selector sets
            post_id: ID of the post
            url: URL of the post

        Returns:
            dict: Post data if successful, None otherwise
        """
        title = ""
        content = ""
        author = ""
        published_date = ""
        category = ""

        # Try different sets of selectors
        for selector_set in selectors:
            if not title:
                title_elem = await frame.query_selector(selector_set["title"])
                if title_elem:
                    title = await title_elem.text_content()
                    title = title.strip()
                    logger.info(f"Found title with selector: {selector_set['title']}")

            if not content:
                # Try to get all text content from the article body
                content_elem = await frame.query_selector(selector_set["content"])
                if content_elem:
                    # Get only plain text content, excluding links and image alt text
                    content = await frame.evaluate(
                        """(element) => {
                        function getPlainText(element) {
                            let text = '';
                            
                            // Skip video components entirely
                            if (element.classList && 
                                (element.classList.contains('se-video') || 
                                 (element.classList.contains('se-component') && element.querySelector('.se-video')))) {
                                return '';
                            }
                            
                            // Process only text nodes directly
                            for (const node of element.childNodes) {
                                if (node.nodeType === Node.TEXT_NODE) {
                                    // This is a direct text node
                                    text += node.textContent.trim() + ' ';
                                } else if (node.nodeType === Node.ELEMENT_NODE) {
                                    // Skip videos, images, links, and other non-text elements
                                    if (node.tagName.toLowerCase() !== 'img' && 
                                        node.tagName.toLowerCase() !== 'a' &&
                                        node.tagName.toLowerCase() !== 'iframe' &&
                                        node.tagName.toLowerCase() !== 'script' &&
                                        node.tagName.toLowerCase() !== 'style' &&
                                        !node.classList.contains('se-video') &&
                                        !(node.classList.contains('se-component') && node.querySelector('.se-video'))) {
                                        
                                        // Recursively get text from child elements
                                        text += getPlainText(node);
                                    }
                                }
                            }
                            return text;
                        }
                        
                        return getPlainText(element).trim();
                    }""",
                        content_elem,
                    )

                    content = content.strip()
                    logger.info(
                        f"Found content with selector: {selector_set['content']}"
                    )

            if not author:
                author_elem = await frame.query_selector(selector_set["author"])
                if author_elem:
                    author = await author_elem.text_content()
                    author = author.strip()
                    logger.info(f"Found author with selector: {selector_set['author']}")

            if not published_date:
                date_elem = await frame.query_selector(selector_set["date"])
                if date_elem:
                    published_date = await date_elem.text_content()
                    published_date = published_date.strip()
                    logger.info(f"Found date with selector: {selector_set['date']}")

            # Try to find category
            if not category:
                category_elem = await frame.query_selector(selector_set["category"])
                if category_elem:
                    category = await category_elem.text_content()
                    category = category.strip()
                    logger.info(
                        f"Found category with selector: {selector_set['category']}"
                    )

            # If we found all elements, break the loop
            if title and content and author and published_date and category:
                break

        # If category is still empty, use a default value
        if not category:
            category = "Uncategorized"
            logger.warning(
                f"Category not found for post {post_id}, using default: {category}"
            )

        # Check for missing data
        if not title or not content or not author or not published_date:
            missing_items = []
            if not title:
                missing_items.append("title")
            if not content:
                missing_items.append("content")
            if not author:
                missing_items.append("author")
            if not published_date:
                missing_items.append("date")

            logger.warning(
                f"Missing data in post {post_id}: {', '.join(missing_items)}"
            )
            return None

        return {
            "title": title,
            "content": content,
            "author": author,
            "published_date": published_date,
            "url": url,
            "post_id": post_id,
            "category": category,
        }

    async def scrape_posts(
        self,
        start_post_id: int,
        end_post_id: Optional[int] = None,
        allowed_categories: Optional[List[str]] = None,
        batch_size: int = 100,
    ) -> Tuple[
        List[str], List[str], List[str], List[str], List[str], List[int], List[str]
    ]:
        """
        Scrape multiple posts in a range

        Args:
            start_post_id: Starting post ID to scrape
            end_post_id: Ending post ID to scrape (inclusive, optional)
            allowed_categories: List of categories to collect (if None, collect all)
            batch_size: Number of posts to collect before saving to database (default: 100)

        Returns:
            tuple: Lists containing the scraped data
        """
        title_list = []
        content_list = []
        author_list = []
        published_date_list = []
        url_list = []
        post_id_list = []
        category_list = []

        # Start from the next post after the last one in the database
        current_post_id = start_post_id
        posts_collected = 0
        posts_skipped = 0
        posts_deleted = 0
        posts_saved_batch = 0
        total_saved = 0

        logger.info(f"Starting crawl from post_id: {current_post_id}")
        logger.info(f"Using batch size: {batch_size}")
        if end_post_id:
            logger.info(f"Will stop at post_id: {end_post_id}")
        if allowed_categories:
            logger.info(f"Collecting only these categories: {allowed_categories}")
        else:
            logger.info("No category filter applied - collecting all categories")

        # Continue until we reach the end_post_id or end_post_id is None (which shouldn't happen normally)
        while end_post_id is None or current_post_id <= end_post_id:
            # Always start with the next post after the last one in the database
            current_post_id += 1

            # If we've gone past the end_post_id, break the loop
            if end_post_id and current_post_id > end_post_id:
                logger.info(f"Reached end_post_id: {end_post_id}, stopping crawl")
                break

            # Check if the post already exists in the database
            existing = await self._post_exists_in_db(current_post_id)
            if existing:
                logger.info(
                    f"Post {current_post_id} already exists in database, skipping"
                )
                posts_skipped += 1
                continue

            # Check if the post should be skipped (already saved or deleted)
            should_skip = await self._should_skip_post(current_post_id)
            if should_skip:
                logger.info(
                    f"Post {current_post_id} is already marked as SAVED or DELETED, skipping"
                )
                posts_skipped += 1
                continue

            # Check if we're re-scraping a post with NULL published_date
            is_rescraping = await self._is_rescraping_null_date(current_post_id)
            if is_rescraping:
                logger.info(
                    f"Re-scraping post {current_post_id} because it has NULL published_date"
                )

            post_data = await self.scrape_post(current_post_id, allowed_categories)

            if post_data:
                posts_collected += 1
                posts_saved_batch += 1

                # Append to lists
                title_list.append(post_data["title"])
                content_list.append(post_data["content"])
                author_list.append(post_data["author"])
                published_date_list.append(post_data["published_date"])
                url_list.append(post_data["url"])
                post_id_list.append(post_data["post_id"])
                category_list.append(post_data["category"])

                logger.info(
                    f"Successfully collected post {post_data['post_id']} (Total: {posts_collected})"
                )
                logger.info(f"Category: {post_data['category']}")

                # Save data to database every batch_size posts
                if posts_saved_batch >= batch_size:
                    logger.info(
                        f"Saving batch of {posts_saved_batch} posts to database..."
                    )

                    # Create a tuple of current data for saving
                    batch_data = (
                        title_list,
                        content_list,
                        author_list,
                        published_date_list,
                        url_list,
                        post_id_list,
                        category_list,
                    )

                    # Save the current batch to database
                    saved_count = await self._save_posts_to_db(batch_data)
                    total_saved += saved_count

                    logger.info(
                        f"Saved batch of {saved_count} posts (Total saved: {total_saved})"
                    )

                    # Clear lists for next batch
                    title_list = []
                    content_list = []
                    author_list = []
                    published_date_list = []
                    url_list = []
                    post_id_list = []
                    category_list = []

                    # Reset batch counter
                    posts_saved_batch = 0
            else:
                # Post was inaccessible/deleted, already marked in the scrape_post method
                posts_deleted += 1

        # Save any remaining posts
        if posts_saved_batch > 0:
            logger.info(
                f"Saving final batch of {posts_saved_batch} posts to database..."
            )

            # Create a tuple of remaining data
            final_batch = (
                title_list,
                content_list,
                author_list,
                published_date_list,
                url_list,
                post_id_list,
                category_list,
            )

            # Save the final batch
            saved_count = await self._save_posts_to_db(final_batch)
            total_saved += saved_count

            logger.info(
                f"Saved final batch of {saved_count} posts (Total saved: {total_saved})"
            )

        logger.info(
            f"Finished collecting data. Total posts collected: {posts_collected}, skipped: {posts_skipped}, deleted: {posts_deleted}, saved: {total_saved}"
        )
        logger.info(f"Stopped at post_id: {current_post_id}")

        # Return the last saved batch or empty lists if all data has been saved
        return (
            title_list,
            content_list,
            author_list,
            published_date_list,
            url_list,
            post_id_list,
            category_list,
        )

    @staticmethod
    @sync_to_async
    def _post_exists_in_db(post_id: int) -> bool:
        """
        Check if a post already exists in the database

        Args:
            post_id: The post ID to check

        Returns:
            bool: True if the post exists, False otherwise
        """
        try:
            with transaction.atomic():
                return NaverCafeData.objects.filter(post_id=post_id).exists()
        except Exception as e:
            logger.error(f"Error checking if post {post_id} exists: {e}")
            # In case of error, assume it doesn't exist so we'll try to fetch it
            return False

    @staticmethod
    @sync_to_async
    def _save_posts_to_db(post_data) -> int:
        """
        Save post data to the database

        Args:
            post_data: Tuple of lists containing post data

        Returns:
            int: Number of posts saved
        """
        titles, contents, authors, dates, urls, post_ids, categories = post_data

        saved_count = 0
        for i in range(len(post_ids)):
            try:
                # Create new post (we've already checked for existence before scraping)
                post = NaverCafeData.objects.create(
                    title=titles[i],
                    content=contents[i],
                    author=authors[i],
                    published_date=dates[i],
                    url=urls[i],
                    post_id=post_ids[i],
                    category=categories[i],
                )
                saved_count += 1
                logger.info(f"Saved post {post_ids[i]} to database")

                # Mark as SAVED using a separate transaction
                # Note: We can't use _mark_post_as_saved directly here because it's an async method
                # and we're inside a sync_to_async function
                try:
                    PostStatus.objects.update_or_create(
                        post_id=post_ids[i],
                        defaults={
                            "status": "SAVED",
                            "error_message": None,
                        },
                    )
                except Exception as e:
                    logger.error(f"Error marking post {post_ids[i]} as SAVED: {e}")
            except Exception as e:
                logger.error(f"Error saving post {post_ids[i]} to database: {str(e)}")

        logger.info(f"Total posts saved to database: {saved_count}")
        return saved_count

    @staticmethod
    @sync_to_async
    def _get_error_posts() -> List[int]:
        """
        Get the list of post IDs with ERROR status from the database

        Returns:
            List[int]: List of post IDs with ERROR status
        """
        try:
            with transaction.atomic():
                post_ids = PostStatus.objects.filter(status="ERROR").values_list(
                    "post_id", flat=True
                )
                return list(post_ids)
        except Exception as e:
            logger.error(f"Error getting posts with ERROR status: {e}")
            # Default to empty list if there's an error
            return []

    async def scrape_error_posts(
        self, batch_size: int = 100, allowed_categories: Optional[List[str]] = None
    ) -> Tuple[
        List[str], List[str], List[str], List[str], List[str], List[int], List[str]
    ]:
        """
        Scrape posts that previously had errors

        Args:
            batch_size: Number of posts to collect before saving to database (default: 100)
            allowed_categories: List of categories to collect (if None, collect all)

        Returns:
            tuple: Lists containing the scraped data
        """
        title_list = []
        content_list = []
        author_list = []
        published_date_list = []
        url_list = []
        post_id_list = []
        category_list = []

        # Get the list of posts with ERROR status
        error_post_ids = await self._get_error_posts()

        if not error_post_ids:
            logger.info("No posts with ERROR status found")
            return (
                title_list,
                content_list,
                author_list,
                published_date_list,
                url_list,
                post_id_list,
                category_list,
            )

        logger.info(f"Found {len(error_post_ids)} posts with ERROR status")

        posts_collected = 0
        posts_skipped = 0
        posts_deleted = 0
        posts_saved_batch = 0
        total_saved = 0

        # Process each post with ERROR status
        for post_id in error_post_ids:
            # Check if the post should be skipped (already saved or deleted)
            should_skip = await self._should_skip_post(post_id)
            if should_skip:
                logger.info(
                    f"Post {post_id} is already marked as SAVED or DELETED, skipping"
                )
                posts_skipped += 1
                continue

            # Check if we're re-scraping a post with NULL published_date
            is_rescraping = await self._is_rescraping_null_date(post_id)
            if is_rescraping:
                logger.info(
                    f"Re-scraping post {post_id} because it has NULL published_date"
                )

            # Try to scrape the post
            post_data = await self.scrape_post(post_id, allowed_categories)

            if post_data:
                posts_collected += 1
                posts_saved_batch += 1

                # Append to lists
                title_list.append(post_data["title"])
                content_list.append(post_data["content"])
                author_list.append(post_data["author"])
                published_date_list.append(post_data["published_date"])
                url_list.append(post_data["url"])
                post_id_list.append(post_data["post_id"])
                category_list.append(post_data["category"])

                logger.info(
                    f"Successfully collected post {post_data['post_id']} (Total: {posts_collected})"
                )
                logger.info(f"Category: {post_data['category']}")

                # Save data to database every batch_size posts
                if posts_saved_batch >= batch_size:
                    logger.info(
                        f"Saving batch of {posts_saved_batch} posts to database..."
                    )

                    # Create a tuple of current data for saving
                    batch_data = (
                        title_list,
                        content_list,
                        author_list,
                        published_date_list,
                        url_list,
                        post_id_list,
                        category_list,
                    )

                    # Save the current batch to database
                    saved_count = await self._save_posts_to_db(batch_data)
                    total_saved += saved_count

                    logger.info(
                        f"Saved batch of {saved_count} posts (Total saved: {total_saved})"
                    )

                    # Clear lists for next batch
                    title_list = []
                    content_list = []
                    author_list = []
                    published_date_list = []
                    url_list = []
                    post_id_list = []
                    category_list = []

                    # Reset batch counter
                    posts_saved_batch = 0
            else:
                # Post still has issues
                posts_deleted += 1

        # Save any remaining posts
        if posts_saved_batch > 0:
            logger.info(
                f"Saving final batch of {posts_saved_batch} posts to database..."
            )

            # Create a tuple of remaining data
            final_batch = (
                title_list,
                content_list,
                author_list,
                published_date_list,
                url_list,
                post_id_list,
                category_list,
            )

            # Save the final batch
            saved_count = await self._save_posts_to_db(final_batch)
            total_saved += saved_count

            logger.info(
                f"Saved final batch of {saved_count} posts (Total saved: {total_saved})"
            )

        logger.info(
            f"Finished processing error posts. Total posts collected: {posts_collected}, skipped: {posts_skipped}, failed again: {posts_deleted}, saved: {total_saved}"
        )

        # Return the last saved batch or empty lists if all data has been saved
        return (
            title_list,
            content_list,
            author_list,
            published_date_list,
            url_list,
            post_id_list,
            category_list,
        )

    async def _get_ingested_posts_id(self, index):
        """
        Get all existing IDs from a Pinecone index using pagination.

        Returns:
            list of all vector IDs in the index
        """

        # Default limit is 100 per page
        response = list(index.list())
        temp_list = list()
        for i in response:
            temp_list += i

        return temp_list

    async def _check_if_posts_exist(self, posts_to_check: list):
        """
        check if the post exists

        Returns:
            list of all posts id that deleted.
        """
        deleted_posts = []
        for post in posts_to_check:
            temp = await self.scrape_post(post)
            if temp == None:
                deleted_posts.append(post)
        return post

    async def run(
        self,
        start_id: Optional[int] = None,
        end_id: Optional[int] = None,
        batch_size: int = 100,
        only_error: bool = False,
        delete_mode: bool = False,
    ) -> None:
        """
        Run the scraper

        Args:
            start_id: Starting post ID to scrape (overrides the last post in database)
            end_id: Ending post ID to scrape (inclusive)
            batch_size: Number of posts to collect before saving to database (default: 100)
            only_error: Whether to only scrape posts with ERROR status
        """
        try:
            # Setup browser
            if not await self.setup():
                logger.error("Failed to set up browser. Exiting.")
                return

            # Navigate to cafe main page
            if not await self.navigate_with_retry(self.cafe_url):
                logger.error("Failed to navigate to Naver Cafe. Exiting.")
                return

            # Login
            login_success = await self.login()

            if not login_success:
                # If automatic login fails, prompt for manual login
                logger.info(
                    "Automatic login failed. Please log in manually if prompted."
                )
                input(
                    "Please log in to Naver if prompted, then press Enter to continue..."
                )
            else:
                logger.info("Successfully logged in to Naver")
                # Wait longer after successful login to ensure everything is loaded
                logger.info("Waiting for page to fully load after login...")
                await asyncio.sleep(self.config["login"]["login_wait_time"])

            # Sync NaverCafeData with PostStatus table
            logger.info(
                "Syncing PostStatus table with existing NaverCafeData entries..."
            )
            synced_count = await self._sync_post_status_with_db()
            logger.info(f"Synced {synced_count} posts with SAVED status")

            logger.info("Crawler behavior:")
            logger.info("1. Skipping posts marked as DELETED")
            logger.info("2. Skipping posts marked as SAVED with valid published_date")
            logger.info("3. Re-scraping posts marked as SAVED with NULL published_date")
            logger.info("4. Attempting to scrape posts marked as ERROR")
            logger.info("5. Attempting to scrape posts not yet in PostStatus table")

            # Get allowed categories from database but don't use them for filtering
            allowed_categories = await self._get_allowed_categories()
            if allowed_categories:
                logger.info(
                    f"Found these categories in the database (for reference): {allowed_categories}"
                )
            else:
                logger.info("No categories found in database.")
            logger.info("Collecting all posts regardless of category.")

            # If only_error flag is set, scrape only posts with ERROR status
            if only_error:
                logger.info("Only scraping posts with ERROR status")
                await self.scrape_error_posts(
                    batch_size=batch_size,
                    allowed_categories=None,  # Pass None to collect all categories
                )
                return

            if not delete_mode:
                # Regular scraping workflow
                # Determine start_post_id
                start_post_id = await self._determine_start_id(start_id)

                # Determine end_post_id
                end_post_id = await self._determine_end_id(end_id)

                # Get post data - pass None for allowed_categories to collect all
                post_data = await self.scrape_posts(
                    start_post_id,
                    end_post_id=end_post_id,
                    allowed_categories=None,  # Pass None to collect all categories
                    batch_size=batch_size,
                )

                # Check if there's any remaining data to save
                # No need to save data again since it's already saved in batches during scraping
                if post_data and any(post_data):
                    logger.info("Crawler finished processing all posts")
                else:
                    logger.info("No data collected")
            else:
                PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
                PINECONE_INDEX_NAME = os.environ["PINECONE_INDEX_NAME"]
                # Initialize Pinecone for filtering ids
                pc = Pinecone(api_key=PINECONE_API_KEY)
                index = pc.Index(PINECONE_INDEX_NAME)
                # 1. Get all ingested post id
                ingested_posts_id: list = await self._get_ingested_posts_id(index=index)
                # 2. Scrape again the posts
                deleted_posts_id: list = await self._check_if_posts_exist(
                    posts_to_check=ingested_posts_id
                )
                # 3. delete ids from index
                index.delete(ids=list(deleted_posts_id))
                # 4. delte ids from db
                NaverCafeData.objects.filter(post_id__in=deleted_posts_id).delete()

        except Exception as e:
            logger.error(f"Error during main execution: {e}")
            logger.debug(traceback.format_exc())
        finally:
            await self.cleanup()

    async def _determine_start_id(self, start_id: Optional[int]) -> int:
        """Determine the starting post ID"""
        if start_id is not None:
            # Use the provided start_id
            start_post_id = start_id
            logger.info(f"Using provided start_post_id: {start_post_id}")
        else:
            # Check last post_id of NaverCafeData
            last_post_id = await self._get_last_post()
            if last_post_id:
                logger.info(f"Last post ID in database: {last_post_id}")
                start_post_id = last_post_id
            else:
                logger.info("No post_id found in NaverCafeData, starting from ID 1")
                start_post_id = 1
        return start_post_id

    async def _determine_end_id(self, end_id: Optional[int]) -> Optional[int]:
        """Determine the ending post ID"""
        if end_id is not None:
            # Use the provided end_id
            end_post_id = end_id
            logger.info(f"Using provided end_post_id: {end_post_id}")
        else:
            # Get the latest post ID from the cafe main page
            end_post_id = await self.get_latest_post_id()
            if end_post_id:
                logger.info(f"Latest post ID in cafe: {end_post_id}")
            else:
                logger.info(
                    "Could not determine latest post ID, will crawl indefinitely"
                )
                end_post_id = None
        return end_post_id

    @staticmethod
    @sync_to_async
    def _get_last_post() -> Optional[int]:
        """Get the last post ID from the database"""
        try:
            with transaction.atomic():
                last_post = NaverCafeData.objects.order_by("post_id").last()
                return last_post.post_id if last_post else None
        except Exception as e:
            logger.error(f"Error getting last post: {e}")
            return None

    @staticmethod
    @sync_to_async
    def _get_allowed_categories() -> List[str]:
        """Get the list of allowed categories from the database"""
        try:
            with transaction.atomic():
                categories = AllowedCategory.objects.filter(is_active=True).values_list(
                    "name", flat=True
                )
                return list(categories)
        except Exception as e:
            logger.error(f"Error getting allowed categories: {e}")
            # Default to empty list if there's an error
            return []

    @staticmethod
    @sync_to_async
    def _sync_post_status_with_db() -> int:
        """
        Sync the PostStatus table with NaverCafeData

        Marks all posts that exist in NaverCafeData as SAVED in the PostStatus table
        if they don't already have a status.

        Returns:
            int: Number of posts marked as SAVED
        """
        try:
            with transaction.atomic():
                # Get all post_ids from NaverCafeData
                all_post_ids = set(
                    NaverCafeData.objects.values_list("post_id", flat=True)
                )

                # Get post_ids that already have a status
                existing_status_ids = set(
                    PostStatus.objects.values_list("post_id", flat=True)
                )

                # Find post_ids that need to be marked as SAVED
                posts_to_mark = all_post_ids - existing_status_ids

                # Create PostStatus entries for these posts
                post_status_objects = [
                    PostStatus(post_id=post_id, status="SAVED")
                    for post_id in posts_to_mark
                ]

                # Bulk create the objects
                if post_status_objects:
                    PostStatus.objects.bulk_create(post_status_objects)

                logger.info(
                    f"Synced {len(posts_to_mark)} posts from NaverCafeData to PostStatus as SAVED"
                )
                return len(posts_to_mark)
        except Exception as e:
            logger.error(f"Error syncing PostStatus with NaverCafeData: {e}")
            return 0

    @staticmethod
    @sync_to_async
    def _is_rescraping_null_date(post_id: int) -> bool:
        """
        Check if a post should be re-scraped because it has NULL published_date

        Args:
            post_id: The post ID to check

        Returns:
            bool: True if the post should be re-scraped, False otherwise
        """
        try:
            with transaction.atomic():
                # Check if this post exists in NaverCafeData with a NULL published_date
                post_with_null_date = NaverCafeData.objects.filter(
                    post_id=post_id, published_date__isnull=True
                ).exists()

                # If it has a NULL date, return True to re-scrape it
                return post_with_null_date
        except Exception as e:
            logger.error(f"Error checking if post {post_id} should be re-scraped: {e}")
            return False


async def main(start_id=None, end_id=None, batch_size=100, only_error=False):
    """
    Main function to run the crawler

    Args:
        start_id: Starting post ID to crawl from (overrides the last post in database)
        end_id: Ending post ID to crawl to (inclusive)
        batch_size: Number of posts to collect before saving to database (default: 100)
        only_error: Whether to only scrape posts with ERROR status
    """
    scraper = NaverCafeScraper(cafe_url="https://cafe.naver.com/cjdckddus/")
    await scraper.run(start_id, end_id, batch_size, only_error)


async def sync_db_with_cafe_data():
    """
    1. Get all ingested post id
    2. Scrape again the posts
    3. Update post status
    4. Attempt delete all post_id in pinecone which post status is not saved
    """
    scraper = NaverCafeScraper(cafe_url="https://cafe.naver.com/cjdckddus/")
    await scraper.run(
        delete_mode=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
