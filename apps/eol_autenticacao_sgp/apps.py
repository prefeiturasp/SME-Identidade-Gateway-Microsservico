"""Configuração do app eol_autenticacao_sgp."""

from django.apps import AppConfig


class EolAutenticacaoSgpConfig(AppConfig):
    """Configura a compatibilidade com a autenticação legada do SGP."""

    name = "apps.eol_autenticacao_sgp"
    label = "eol_autenticacao_sgp"
