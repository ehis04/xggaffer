"""Shared DRF pagination classes."""
from rest_framework.pagination import PageNumberPagination


class StandardPageNumberPagination(PageNumberPagination):
    """Base pagination; override page_size and max_page_size per app."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
