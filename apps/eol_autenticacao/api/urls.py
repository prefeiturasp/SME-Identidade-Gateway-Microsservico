"""Caminhos completos dos endpoints legados de autenticação."""

from django.urls import path, re_path

from apps.eol_autenticacao.api.views import (
    AlterarSenhaView,
    RecuperarSenhaView,
    ValidarTokenView,
)

app_name = "eol_autenticacao"

urlpatterns = [
    path(
        "RecuperarSenha/usuario",
        RecuperarSenhaView.as_view(),
        name="recuperar-senha",
    ),
    path(
        "RecuperarSenha/token/validar",
        ValidarTokenView.as_view(),
        name="validar-token-recuperacao",
    ),
    re_path(
        r"^AlterarSenha/?$", AlterarSenhaView.as_view(), name="alterar-senha"
    ),
]
