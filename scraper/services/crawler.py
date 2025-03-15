import asyncio
import logging
import os
import random
import time
import traceback

import dotenv
import pandas as pd
from asgiref.sync import sync_to_async
from django.db import transaction
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from scraper.models import NaverCafeData

dotenv.load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("naver_cafe_scraper.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Constants
NAVER_CAFE_URL = "https://cafe.naver.com/cjdckddus/"


@sync_to_async
def get_last_post():
    """Get the last post ID from the database"""
    try:
        with transaction.atomic():
            last_post = NaverCafeData.objects.order_by("post_id").last()
            return last_post.post_id if last_post else None
    except Exception as e:
        logger.error(f"Error getting last post: {e}")
        return None


async def login_to_naver(page):
    """
    Automatically log in to Naver using credentials from .env file

    Args:
        page: Playwright page object

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
        if "nid.naver.com" not in page.url:
            # Find and click the login button
            login_button = await page.query_selector(".gnb_btn_login")
            if login_button:
                # Add a small random delay before clicking (like a human would)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                await login_button.click()
                # Wait for navigation to login page
                await page.wait_for_load_state("networkidle")
            else:
                logger.warning(
                    "Login button not found, trying to navigate directly to login page"
                )
                if not await navigate_with_retry(
                    page, "https://nid.naver.com/nidlogin.login"
                ):
                    return False

        # Wait for the login form to be visible
        await page.wait_for_selector("#id", timeout=10000)

        # Random delay before starting to type (like a human would pause)
        await asyncio.sleep(random.uniform(0.8, 2.0))

        # Clear the fields first (sometimes auto-filled)
        await page.click("#id")
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Delete")

        # Type ID with human-like delays between keystrokes
        for char in naver_id:
            await page.type("#id", char, delay=random.uniform(50, 150))
            # Occasionally add a longer pause as if thinking
            if random.random() < 0.2:
                await asyncio.sleep(random.uniform(0.1, 0.3))

        # Random delay before moving to password field (like a human would)
        await asyncio.sleep(random.uniform(0.5, 1.2))

        # Click on password field
        await page.click("#pw")

        # Type password with human-like delays
        for char in naver_pw:
            await page.type("#pw", char, delay=random.uniform(70, 170))
            # Occasionally add a longer pause
            if random.random() < 0.2:
                await asyncio.sleep(random.uniform(0.1, 0.3))

        # Random delay before clicking login button (like a human would)
        await asyncio.sleep(random.uniform(0.7, 1.5))

        # Click the login button
        await page.click(".btn_login")

        # Wait for navigation after login - increase timeout and wait for multiple load states
        await page.wait_for_load_state("networkidle", timeout=30000)
        await page.wait_for_load_state("domcontentloaded", timeout=30000)

        # Give extra time for the page to fully load and process the login
        await asyncio.sleep(5)

        # Better login success detection
        if "cafe.naver.com" in page.url or (
            "naver.com" in page.url and "nid.naver.com/nidlogin" not in page.url
        ):
            logger.info("Login successful")
            return True

        # Check for login error messages
        error_msg = await page.query_selector(".error_message")
        if error_msg:
            error_text = await error_msg.text_content()
            logger.error(f"Login failed: {error_text}")
            return False

        # If we can find elements that indicate we're logged in
        if await page.query_selector(".gnb_my_li") or await page.query_selector(
            ".gnb_name"
        ):
            logger.info("Login successful based on UI elements")
            return True

        logger.warning("Login status unclear - proceeding with caution")
        return True

    except Exception as e:
        logger.error(f"Error during login: {e}")
        logger.debug(traceback.format_exc())
        return False


async def setup_browser():
    """
    Set up and return a Playwright browser instance

    Returns:
        tuple: (playwright, browser, page) objects
    """
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    return playwright, browser, page


async def navigate_with_retry(page, url, max_retries=3, timeout=60000):
    """
    Navigate to a URL with retry logic for handling timeouts

    Args:
        page: Playwright page object
        url: URL to navigate to
        max_retries: Maximum number of retry attempts
        timeout: Timeout in milliseconds for each attempt

    Returns:
        bool: True if navigation was successful, False otherwise
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Navigation attempt {attempt}/{max_retries} to {url}")
            await page.goto(url, timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            logger.warning(
                f"Timeout on attempt {attempt}/{max_retries} navigating to {url}"
            )
            if attempt < max_retries:
                # Wait before retrying (increasing backoff)
                wait_time = 5 * attempt  # 5, 10, 15 seconds...
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


async def main():
    playwright = None
    browser = None
    try:
        # 브라우저 설정
        playwright, browser, page = await setup_browser()
        if not await navigate_with_retry(page, NAVER_CAFE_URL):
            logger.error("Failed to navigate to Naver Cafe. Exiting.")
            return

        # 로그인
        login_success = await login_to_naver(page)

        if not login_success:
            # If automatic login fails, prompt for manual login
            logger.info("Automatic login failed. Please log in manually if prompted.")
            input("Please log in to Naver if prompted, then press Enter to continue...")
        else:
            logger.info("Successfully logged in to Naver")
            # Wait longer after successful login to ensure everything is loaded
            logger.info("Waiting for page to fully load after login...")
            await asyncio.sleep(10)

        # check last post_id of NaverCafeData
        last_post_id = await get_last_post()
        if last_post_id:
            logger.info(f"last post ID: {last_post_id}")
        else:
            logger.info("No post_id found in NaverCafeData")

    except Exception as e:
        logger.error(f"Error during main execution: {e}")
        logger.debug(traceback.format_exc())
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()


if __name__ == "__main__":
    asyncio.run(main())
