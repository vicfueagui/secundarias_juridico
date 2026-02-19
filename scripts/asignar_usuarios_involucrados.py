from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction

from tramites import models

User = get_user_model()

DEFAULT_USERNAMES = [
    "maria.garciago",
    "admin",
    "dulce.luna",
    "claudio.diaz",
    "jaime.pacheco",
    "neggie.rubio",
]

ASESOR_USUARIO = {
    "ANGEL": "angel.canche",
    "ALICIA": "alicia.alcerreca",
    "CARLOS": "carlos.vales",
    "CINDY": "cindy.baeza",
    "SANDY": "sandy.garcia",
}


def _resolve_users(usernames):
    usuarios = list(User.objects.filter(username__in=usernames))
    encontrados = {u.username for u in usuarios}
    faltantes = [u for u in usernames if u not in encontrados]
    return usuarios, faltantes


def main():
    base_usuarios, faltantes_base = _resolve_users(DEFAULT_USERNAMES)
    if faltantes_base:
        print("Usuarios base no encontrados:", ", ".join(faltantes_base))

    casos = (
        models.CasoInterno.objects.select_related("estatus")
        .filter(asunto__iexact="ENTREGADO A ASESOR")
        .exclude(estatus__nombre__iexact="Concluido")
    )

    total_casos = casos.count()
    total_tramites = 0
    casos_actualizados = 0
    tramites_actualizados = 0

    with transaction.atomic():
        for caso in casos.iterator():
            usernames = list(DEFAULT_USERNAMES)
            asesor_key = (caso.asesor_cct or "").strip().upper()
            asesor_username = ASESOR_USUARIO.get(asesor_key)
            if asesor_username:
                usernames.append(asesor_username)
            usuarios, faltantes = _resolve_users(usernames)
            if faltantes:
                print(f"Caso {caso.id}: usuarios faltantes: {', '.join(faltantes)}")
            caso.usuarios_involucrados.add(*usuarios)
            casos_actualizados += 1

            tramites = caso.tramites_relacionados.all()
            total_tramites += tramites.count()
            for tramite in tramites.iterator():
                tramite.usuarios_involucrados.add(*usuarios)
                tramites_actualizados += 1

    print("Casos filtrados:", total_casos)
    print("Casos actualizados:", casos_actualizados)
    print("Tramites asociados:", total_tramites)
    print("Tramites actualizados:", tramites_actualizados)


if __name__ == "__main__":
    main()
