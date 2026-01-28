"""
Pagination classes for Changple Core service.
"""

from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination with configurable page size."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class LargeResultsSetPagination(PageNumberPagination):
    """Pagination for larger result sets."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
