from __future__ import annotations

from django.utils.deprecation import MiddlewareMixin
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.http import HttpResponseForbidden, JsonResponse

from tramites.logging_utils import clear_request_context, set_request_context


class RequestUserLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._logging_start_ts = timezone.now()
        user = getattr(request, "user", None)
        path = getattr(request, "path", None)
        method = getattr(request, "method", None)
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.META.get("REMOTE_ADDR")
        request_id = request.META.get("HTTP_X_REQUEST_ID") or get_random_string(12)
        request.request_id = request_id
        set_request_context(
            user=user,
            path=path,
            method=method,
            client_ip=client_ip,
            request_id=request_id,
        )

    def process_response(self, request, response):
        start_ts = getattr(request, "_logging_start_ts", None)
        duration_ms = None
        if start_ts is not None:
            duration_ms = (timezone.now() - start_ts).total_seconds() * 1000
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.META.get("REMOTE_ADDR")
        set_request_context(
            user=getattr(request, "user", None),
            path=getattr(request, "path", None),
            method=getattr(request, "method", None),
            client_ip=client_ip,
            request_id=getattr(request, "request_id", None),
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        request_id = getattr(request, "request_id", None)
        if request_id:
            response["X-Request-ID"] = request_id
        clear_request_context()
        return response

    def process_exception(self, request, exception):
        clear_request_context()


class FeatureFlagAccessMiddleware(MiddlewareMixin):
    """Restringe módulos por feature flag a nivel backend."""

    MODULE_FLAG_PREFIXES = (
        ("/tramites/herramientas/", "module_herramientas"),
        ("/herramientas/", "module_herramientas"),
        ("/tramites/reportes/", "module_reportes"),
        ("/reportes/", "module_reportes"),
        ("/licencias/", "module_licencias"),
        ("/folios/", "module_tramites"),
        ("/bandeja/", "module_tramites"),
        ("/tramites/", "module_tramites"),
    )
    EXEMPT_PREFIXES = (
        "/admin/",
        "/static/",
        "/media/",
        "/accounts/login",
        "/accounts/logout",
        "/api/token/",
    )

    def process_view(self, request, view_func, view_args, view_kwargs):
        from tramites.services import feature_flags

        path = request.path or ""
        if path == "/":
            return None
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return None
        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            return None
        flag_code = None
        for prefix, code in self.MODULE_FLAG_PREFIXES:
            if path.startswith(prefix):
                flag_code = code
                break
        if not flag_code:
            return None
        enabled = feature_flags.is_enabled(flag_code, user, default_if_missing=True)
        if enabled:
            return None
        if path.startswith("/api/") or request.headers.get("Accept", "").startswith("application/json"):
            return JsonResponse(
                {"detail": "El módulo solicitado está deshabilitado para tu rol."},
                status=403,
            )
        return HttpResponseForbidden("El módulo solicitado está deshabilitado para tu rol.")
