# Study note for understanding cursor codes.

## crawler.py

### Imports:

```python
import asyncio # for asycnio works
import logging # for logging
import os 
import random
import re # to find things using regex
import traceback # don't know for now.
from typing import Any, Dict, List, Optional, Tuple

import dotenv # for get env variables
from asgiref.sync import sync_to_async # don't know
from django.db import transaction # don't know maybe it's for consistency
from playwright.async_api import Browser, BrowserContext, ElementHandle, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from scraper.models import AllowedCategory, NaverCafeData, PostStatus
```

