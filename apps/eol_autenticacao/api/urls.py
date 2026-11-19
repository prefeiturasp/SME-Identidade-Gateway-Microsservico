"""Caminhos completos dos endpoints legados de autenticação."""

from django.urls import path

from apps.eol_autenticacao.api.views import AutenticacaoExternaView

urlpatterns = [
    path(
        "externa/",
        AutenticacaoExternaView.as_view(),
        name="eol-autenticacao-externa",
    ),
]
