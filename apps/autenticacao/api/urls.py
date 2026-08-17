"""Rotas do domínio de login e níveis de acesso."""

from django.urls import path

from apps.autenticacao.api.views import (
    DadosAcessoView,
    DadosUsuarioView,
    LoginView,
    LogoutView,
    PerfisPorLoginView,
)
from apps.autenticacao.api.views_credenciais import (
    AlterarEmailView,
    AlterarSenhaView,
)

# RecuperarSenhaView desativada temporariamente: send_update_account
# está instável no Keycloak de QA (502 recorrente). Reativar bastando
# devolver a rota "recuperar-senha/" e o import correspondente.
urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path(
        "usuarios/<str:login>/dados/",
        DadosUsuarioView.as_view(),
        name="usuario-dados",
    ),
    path(
        "usuarios/<str:login>/perfis/",
        PerfisPorLoginView.as_view(),
        name="usuario-perfis",
    ),
    path(
        "usuarios/<str:login>/perfis/<str:perfil>/acesso/",
        DadosAcessoView.as_view(),
        name="usuario-dados-acesso",
    ),
    path(
        "alterar-senha/",
        AlterarSenhaView.as_view(),
        name="alterar-senha",
    ),
    path(
        "alterar-email/",
        AlterarEmailView.as_view(),
        name="alterar-email",
    ),
]
