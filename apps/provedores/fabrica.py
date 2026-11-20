"""Seleção do adaptador de identidade pela configuração da aplicação."""

from typing import cast

from django.conf import settings
from django.utils.module_loading import import_string

from apps.provedores.contratos import ProvedorIdentidade
from apps.provedores.excecoes import ProvedorIndisponivelError


def obter_provedor_identidade() -> ProvedorIdentidade:
    """Cria o adaptador configurado sem expor o SDK aos serviços.

    Returns:
        Implementação do contrato ProvedorIdentidade.

    Raises:
        ProvedorIndisponivelError: Se a configuração não puder ser carregada.
    """
    try:
        return cast(
            ProvedorIdentidade, import_string(settings.PROVEDOR_IDENTIDADE)()
        )
    except (ImportError, TypeError) as erro:
        raise ProvedorIndisponivelError from erro
