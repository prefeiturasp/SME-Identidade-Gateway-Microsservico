"""Erros de integração independentes do SDK do provedor."""


class ProvedorIndisponivelError(Exception):
    """Não foi possível concluir ou confirmar a operação no provedor."""


class ContaNaoEncontradaError(Exception):
    """A conta consultada não existe no contexto de identidade."""


class PoliticaSenhaIncompativelError(Exception):
    """O provedor não atende à política de histórico exigida."""


class AlteracaoSenhaRejeitadaError(Exception):
    """O provedor confirmou que a nova senha não foi aplicada."""


class SenhaNoHistoricoError(AlteracaoSenhaRejeitadaError):
    """A senha já consta no histórico de credenciais da conta."""


class SenhaForaPoliticaError(AlteracaoSenhaRejeitadaError):
    """A senha foi rejeitada pela política de credenciais do provedor."""
