from __future__ import annotations

import threading


_context = threading.local()


def set_request_context(
    *,
    user=None,
    path: str | None = None,
    method: str | None = None,
    client_ip: str | None = None,
    request_id: str | None = None,
    status_code: int | None = None,
    duration_ms: float | None = None,
) -> None:
    _context.user = user
    _context.path = path
    _context.method = method
    _context.client_ip = client_ip
    _context.request_id = request_id
    _context.status_code = status_code
    _context.duration_ms = duration_ms


def clear_request_context() -> None:
    _context.user = None
    _context.path = None
    _context.method = None
    _context.client_ip = None
    _context.request_id = None


def get_request_user() -> str:
    user = getattr(_context, "user", None)
    if not user:
        return "-"
    if hasattr(user, "get_username"):
        return user.get_username()
    return str(user)


def get_request_user_id() -> str:
    user = getattr(_context, "user", None)
    if not user:
        return "-"
    user_id = getattr(user, "pk", None)
    return str(user_id) if user_id is not None else "-"


def get_request_user_object():
    return getattr(_context, "user", None)


def get_request_path() -> str:
    path = getattr(_context, "path", None)
    return path or "-"


def get_request_method() -> str:
    method = getattr(_context, "method", None)
    return method or "-"


def get_request_ip() -> str:
    ip = getattr(_context, "client_ip", None)
    return ip or "-"


def get_request_id() -> str:
    request_id = getattr(_context, "request_id", None)
    return request_id or "-"


def get_request_status_code() -> str:
    status_code = getattr(_context, "status_code", None)
    return str(status_code) if status_code is not None else "-"


def get_request_duration_ms() -> str:
    duration_ms = getattr(_context, "duration_ms", None)
    if duration_ms is None:
        return "-"
    return f"{duration_ms:.1f}"


class RequestUserLogFilter:
    def filter(self, record):  # pragma: no cover
        record.user = get_request_user()
        record.user_id = get_request_user_id()
        record.path = get_request_path()
        record.method = get_request_method()
        record.client_ip = get_request_ip()
        record.request_id = get_request_id()
        record.status_code = get_request_status_code()
        record.duration_ms = get_request_duration_ms()
        return True


class ModuleNameLogFilter:
    def filter(self, record):  # pragma: no cover
        name = record.name or ""
        if name.startswith("tramites"):
            record.module_name = "tramites"
        elif name.startswith("licencias"):
            record.module_name = "licencias"
        elif name.startswith("django"):
            record.module_name = "django"
        else:
            record.module_name = name.split(".")[0] if name else "-"
        return True


class ExactLevelFilter:
    def __init__(self, level_name: str):
        self.level_name = level_name

    def filter(self, record):  # pragma: no cover
        return record.levelname == self.level_name
