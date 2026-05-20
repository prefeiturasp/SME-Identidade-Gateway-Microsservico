from django.urls import path

from . import views

urlpatterns = [
    path("autenticacao", views.autenticacao, name="legacy-autenticacao"),
    path(
        "autenticacaoSgp/CarregarPerfisPorLogin/<str:login>",
        views.carregar_perfis,
        name="legacy-perfis",
    ),
    path(
        "autenticacaoSgp/<str:login>/dados",
        views.dados_usuario,
        name="legacy-dados",
    ),
    path(
        "autenticacaoSgp/CarregarDadosAcesso/usuarios/<str:usuario_id>/perfis/<str:perfil_id>",
        views.carregar_dados_acesso,
        name="legacy-dados-acesso",
    ),
]
