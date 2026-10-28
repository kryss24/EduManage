"""Pagination standard de l'application EduManage."""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Pagination avec taille de page par défaut et plafond de taille maximale."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
