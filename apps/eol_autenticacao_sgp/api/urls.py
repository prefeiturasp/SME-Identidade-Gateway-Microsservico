"""Caminhos completos dos endpoints legados de autenticação do SGP."""

from django.urls import path

from apps.eol_autenticacao_sgp.api import views

urlpatterns = [
    path(
        "<str:login>/ValidarEmailExistente/<str:email>",
        views.ValidarEmailExistenteView.as_view(),
        name="validar-email-existente",
    ),
]
