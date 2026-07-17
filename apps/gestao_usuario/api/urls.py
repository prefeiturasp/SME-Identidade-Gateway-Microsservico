"""Rotas do domínio de gestão de usuário."""

from django.urls import path

from apps.gestao_usuario.api.views import (
    ConcederAcessoView,
    ConsultarIdentidadeView,
    CriarUsuarioView,
    SincronizarUsuarioView,
)

urlpatterns = [
    path("", CriarUsuarioView.as_view(), name="usuario-criar"),
    path(
        "sincronizar/",
        SincronizarUsuarioView.as_view(),
        name="usuario-sincronizar",
    ),
    path(
        "conceder-acesso/",
        ConcederAcessoView.as_view(),
        name="usuario-conceder-acesso",
    ),
    path(
        "consultar/",
        ConsultarIdentidadeView.as_view(),
        name="usuario-consultar",
    ),
]
