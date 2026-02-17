"""
Scraper pipeline package.

Provides abstract interfaces and implementations for the
scrape → process → embed → store pipeline.
"""

from src.scraper.pipeline.base import ContentSource as ContentSource
from src.scraper.pipeline.orchestrator import (
    PipelineOrchestrator as PipelineOrchestrator,
)
from src.scraper.pipeline.orchestrator import (
    get_default_pipeline as get_default_pipeline,
)
