"""Pagination helpers used by every list endpoint.

Endpoints declare page/page_size query params; `paginate_qs` slices the
queryset and returns items + pagination meta so all screens share one shape.
"""


def paginate_qs(qs, page: int = 1, page_size: int = 20):
    page_size = max(1, min(page_size, 200))
    page = max(1, page)
    total = qs.count()
    start = (page - 1) * page_size
    items = list(qs[start : start + page_size])
    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size if total else 0,
        },
    }