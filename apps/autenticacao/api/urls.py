"""Rotas do domínio de login e níveis de acesso."""

from django.urls import path

from apps.autenticacao.api.views import (
    ClientTokenView,
    DadosAcessoView,
    DadosUsuarioView,
    LoginView,
    LogoutNotificacaoView,
    LogoutView,
    PerfisPorLoginView,
    SistemasPorLoginView,
    ValidarClientTokenView,
    ValidarTokenView,
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
        "cliente/login/",
        ClientTokenView.as_view(),
        name="cliente-login",
    ),
    path(
        "cliente/validar-token/",
        ValidarClientTokenView.as_view(),
        name="validar-cliente-token",
    ),
    path(
        "validar-token/",
        ValidarTokenView.as_view(),
        name="validar-token",
    ),
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
        "usuarios/<str:login>/sistemas/",
        SistemasPorLoginView.as_view(),
        name="usuario-sistemas",
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
    path(
        "logout-notificacao/",
        LogoutNotificacaoView.as_view(),
        name="logout-notificacao",
    ),
]
