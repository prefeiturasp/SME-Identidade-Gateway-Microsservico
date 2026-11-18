"""Caminhos completos dos endpoints legados de autenticação do SGP."""

from django.urls import path

from apps.eol_autenticacao_sgp.api.views import DadosUsuarioView

urlpatterns = [
    path(
        "<str:login>/dados/",
        DadosUsuarioView.as_view(),
        name="eol-autenticacao-sgp-dados-usuario",
    ),
]
