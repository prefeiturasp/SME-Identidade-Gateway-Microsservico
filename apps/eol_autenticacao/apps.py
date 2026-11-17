"""Configuração do app eol_autenticacao."""

from django.apps import AppConfig


class EolAutenticacaoConfig(AppConfig):
    """Configura a compatibilidade com a autenticação legada."""

    name = "apps.eol_autenticacao"
    label = "eol_autenticacao"
