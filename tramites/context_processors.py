from __future__ import annotations

from tramites import models


def bandeja_unread_count(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"bandeja_unread_count": 0}
    count = models.BandejaNotificacionDestinatario.objects.filter(
        usuario=request.user,
        leido=False,
    ).count()
    return {"bandeja_unread_count": count}
