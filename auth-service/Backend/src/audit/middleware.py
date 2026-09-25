"""Captures the acting user + client IP in thread-local storage so the audit
signals can attribute every write to the person who made it."""

import threading

_state = threading.local()

_IP_HEADERS = ("HTTP_X_FORWARDED_FOR", "HTTP_X_REAL_IP")


def _client_ip(request):
    for header in _IP_HEADERS:
        value = request.META.get(header)
        if value:
            first = value.split(",")[0].strip()
            if first:
                return first
    return request.META.get("REMOTE_ADDR")


def set_current_user(user, request=None):
    _state.user = user
    if request is not None:
        _state.ip = _client_ip(request)


def set_client_ip(ip):
    _state.ip = ip


def get_current_user():
    return getattr(_state, "user", None)


def get_client_ip():
    return getattr(_state, "ip", None)


def clear():
    _state.user = None
    _state.ip = None


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_client_ip(_client_ip(request))
        try:
            return self.get_response(request)
        finally:
            clear()