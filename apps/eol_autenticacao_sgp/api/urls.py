"""Caminhos completos dos endpoints legados de autenticação do SGP."""

from django.urls import path

from apps.eol_autenticacao_sgp.api.views import (
    DadosUsuarioView,
    ValidarEmailExistenteView,
)

urlpatterns = [
    path(
        "<str:login>/ValidarEmailExistente/<str:email>",
        ValidarEmailExistenteView.as_view(),
        name="validar-email-existente",
    ),
    path(
        "<str:login>/dados/",
        DadosUsuarioView.as_view(),
        name="eol-autenticacao-sgp-dados-usuario",
    )
]
