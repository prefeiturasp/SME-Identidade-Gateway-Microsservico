"""Views do fluxo de login e níveis de acesso.

Endpoints de entrada do Gateway para o domínio de autenticação e
autorização. Todas consultam serviços reais: ``LoginView`` e
``DadosUsuarioView`` falam com o Keycloak (via
``apps.autenticacao.keycloak_admin``, mesmo padrão do comando
``validar_login`` do SME-Identidade-ETL); ``LoginView``,
``PerfisPorLoginView`` e ``DadosAcessoView`` também consultam a
projeção de autorização no SME-Identidade-Token-Microsservico (via
``apps.core.clientes.token_ms``), responsável por gerar o token
enriquecido a partir dos dados da conta e da projeção do usuário.

``LoginView`` já devolve a resposta completa numa única chamada
(token enriquecido + claims + perfis + permissões), sem exigir uma
segunda requisição a ``DadosAcessoView``. As demais views seguem
disponíveis para consulta avulsa (ex.: recarregar perfis sem logar
de novo).

Todas as views exigem autenticação via ``AutenticacaoApiKey``, no
mesmo padrão usado pelo SME-Identidade-ETL e pelo
SME-Identidade-Token-Microsservico.
"""

import httpx
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autenticacao import keycloak_admin
from apps.autenticacao.api.serializers import (
    DadosAcessoResponseSerializer,
    DadosUsuarioResponseSerializer,
    LoginRequestSerializer,
    LoginResponseSerializer,
    LogoutRequestSerializer,
    LogoutResponseSerializer,
    PerfisPorLoginResponseSerializer,
)
from apps.autenticacao.api_key import AutenticacaoApiKey
from apps.autenticacao.gatilho_auditoria import disparar_gatilho
from apps.autenticacao.keycloak_admin import ERRO_USUARIO_NAO_ENCONTRADO
from apps.core.clientes.token_ms import cliente_token_ms
from apps.core.http import resposta_do_servico

_TOKEN_MS_INDISPONIVEL = {"erro": "token-ms indisponível"}


def _obter_token_enriquecido(
    conta_keycloak: dict,
    perfil: str | None,
) -> dict | None:
    """Obtém o token enriquecido gerado pelo Token-MS.

    O Token-MS é responsável por montar e assinar o token
    enriquecido. Em caso de indisponibilidade do serviço ou ausência
    de dados para o usuário, retorna ``None`` para que o login não
    falhe por causa de uma dependência complementar.

    Args:
        conta_keycloak: Dados da conta autenticada no Keycloak.
        perfil: Identificador do perfil selecionado pelo usuário.

    Returns:
        Corpo da resposta contendo o token enriquecido e sua data de
        expiração, ou ``None`` caso não seja possível obtê-los.
    """
    try:
        with cliente_token_ms() as cliente:
            resposta = cliente.post(
                f"/api/v1/token/enriquecido/{conta_keycloak['kc_user_id']}/",
                json={
                    **conta_keycloak,
                    "perfil": perfil,
                },
            )
    except httpx.HTTPError:
        return None

    if resposta.status_code != 200:
        return None
    corpo: dict = resposta.json()
    return corpo


class LoginView(APIView):
    """Autentica um usuário no Keycloak.

    Equivale à Etapa 1 do fluxo legado
    (``POST /api/v1/autenticacao``), mas autentica de verdade contra
    o Keycloak — resolve ``login`` (RF, CPF, e-mail ou username) para
    a conta real e valida a senha via OpenID Connect (grant type
    ``password``).
    """

    authentication_classes = [AutenticacaoApiKey]

    @extend_schema(
        request=LoginRequestSerializer,
        responses=LoginResponseSerializer,
        tags=["Autenticação"],
    )
    def post(self, request: Request) -> Response:
        """Recebe login/senha e autentica contra o Keycloak.

        Resposta completa numa única chamada: além dos tokens OIDC
        brutos do Keycloak, solicita ao Token-MS o token
        enriquecido já gerado e sua data de expiração —
        sem exigir uma segunda requisição a
        ``DadosAcessoView``. Ausência de projeção no Token-MS (ou o
        serviço fora do ar) não bloqueia o login, já a autenticação
        no Keycloak é o que importa: as claims de ``perfis``/
        ``permissoes`` dentro do token enriquecido ficam vazias nesse
        caso.

        Autenticado o usuário, dispara também o gatilho de auditoria
        — acessório e silencioso em caso de falha, pelo mesmo motivo
        que o token enriquecido: o login já aconteceu de verdade no
        Keycloak e não deve ser desfeito por uma dependência
        complementar.

        Args:
            request: Requisição HTTP com ``login`` e ``senha``.

        Returns:
            Identidade autenticada + tokens (OIDC e enriquecido);
            ``401`` se a senha for inválida; ``204`` (sem corpo) se o
            login não existir no Keycloak.
        """
        entrada = LoginRequestSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        resultado = keycloak_admin.autenticar(
            entrada.validated_data["login"],
            entrada.validated_data["senha"],
        )
        if not resultado["autenticado"]:
            if resultado.get("erro") == ERRO_USUARIO_NAO_ENCONTRADO:
                return Response(status=204)
            return Response({"detalhe": resultado["erro"]}, status=401)

        disparar_gatilho(
            settings.KEYCLOAK_REALM,
            resultado.get("kc_user_id"),
        )

        token_enriquecido = (
            _obter_token_enriquecido(resultado, perfil=None) or {}
        )
        resultado["token_enriquecido"] = token_enriquecido.get("token")
        resultado["data_expiracao_token_enriquecido"] = token_enriquecido.get(
            "data_expiracao"
        )

        saida = LoginResponseSerializer(resultado)
        return Response(saida.data)


class LogoutView(APIView):
    """Encerra a sessão de um usuário no Keycloak.

    O Gateway não mantém sessão própria — encerrar a sessão depende
    de repassar ao Keycloak o ``refresh_token`` obtido no login.
    """

    authentication_classes = [AutenticacaoApiKey]

    @extend_schema(
        request=LogoutRequestSerializer,
        responses=LogoutResponseSerializer,
        tags=["Autenticação"],
    )
    def post(self, request: Request) -> Response:
        """Recebe o refresh token e encerra a sessão no Keycloak.

        Dispara também o gatilho de auditoria, no mesmo padrão do
        login — acessório e silencioso em caso de falha.

        Args:
            request: Requisição HTTP com ``refresh_token``.

        Returns:
            Confirmação do encerramento; ``400`` se o
            ``refresh_token`` não vier no corpo.
        """
        entrada = LogoutRequestSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        resultado = keycloak_admin.encerrar_sessao(
            entrada.validated_data["refresh_token"]
        )

        disparar_gatilho(
            settings.KEYCLOAK_REALM,
            resultado.get("kc_user_id"),
        )

        saida = LogoutResponseSerializer({"situacao": "sessao_encerrada"})
        return Response(saida.data)


class DadosUsuarioView(APIView):
    """Retorna dados cadastrais de um usuário, direto no Keycloak.

    Equivale a ``GET /api/AutenticacaoSgp/{login}/dados``.
    """

    authentication_classes = [AutenticacaoApiKey]

    @extend_schema(
        responses=DadosUsuarioResponseSerializer,
        tags=["Autenticação"],
    )
    def get(self, request: Request, login: str) -> Response:
        """Retorna os dados cadastrais de um usuário.

        Args:
            request: Requisição HTTP recebida.
            login: RF, CPF, e-mail ou username do usuário.

        Returns:
            Dados cadastrais do usuário, ou 204 (sem corpo) se não
            encontrado.
        """
        dados = keycloak_admin.obter_dados_usuario(login)
        if not dados:
            return Response(status=204)

        saida = DadosUsuarioResponseSerializer(dados)
        return Response(saida.data)


def _resolver_conta_keycloak(login: str) -> dict | None:
    """Resolve a conta normalizada do Keycloak a partir do login.

    O SME-Identidade-Token-Microsservico indexa a projeção de
    autorização por ``usuario_id`` (UUID igual ao ``kc_user_id`` do
    Keycloak) — não por RF/CPF/e-mail como as rotas deste módulo
    recebem. Reaproveita ``obter_dados_usuario`` (mesma normalização
    usada por ``DadosUsuarioView``) em vez de lidar com o formato
    bruto do Keycloak (``attributes`` como listas) em mais de um
    lugar — o formato retornado já é o esperado pelo
    ``Token-MS``.

    Args:
        login: RF, CPF, e-mail ou username do usuário.

    Returns:
        A conta normalizada (``kc_user_id``, ``username``, ``nome``,
        ``email``, ``ativo``, ``cpf``, ``rf``), ou ``None`` se o
        login não existir no Keycloak.
    """
    return keycloak_admin.obter_dados_usuario(login)


class PerfisPorLoginView(APIView):
    """Retorna os perfis de acesso de um usuário.

    Equivale a
    ``GET /api/AutenticacaoSgp/CarregarPerfisPorLogin/{login}``.
    Resolve o ``kc_user_id`` no Keycloak e consulta a projeção real
    no SME-Identidade-Token-Microsservico.
    """

    authentication_classes = [AutenticacaoApiKey]

    @extend_schema(
        responses=PerfisPorLoginResponseSerializer,
        tags=["Níveis de Acesso"],
    )
    def get(self, request: Request, login: str) -> Response:
        """Retorna os perfis de acesso vinculados ao login.

        Args:
            request: Requisição HTTP recebida.
            login: RF, CPF ou login do usuário.

        Returns:
            Lista de perfis de acesso do usuário; 204 (sem corpo) se
            o login não existir no Keycloak ou não houver projeção
            para ele no Token-MS.
        """
        conta = _resolver_conta_keycloak(login)
        if not conta:
            return Response(status=204)

        try:
            with cliente_token_ms() as cliente:
                resposta = cliente.get(
                    f"/api/v1/perfis/{conta['kc_user_id']}/"
                )
        except httpx.TimeoutException:
            return Response({"erro": "token-ms timeout"}, status=504)
        except httpx.TransportError:
            return Response(_TOKEN_MS_INDISPONIVEL, status=502)

        if resposta.status_code == 404:
            return Response(status=204)
        if resposta.status_code != 200:
            return resposta_do_servico(resposta)

        projecao = resposta.json()
        saida = PerfisPorLoginResponseSerializer(
            {"rf": projecao.get("rf"), "perfis": projecao.get("perfis", [])}
        )
        return Response(saida.data)


class DadosAcessoView(APIView):
    """Retorna o contexto de acesso completo de um usuário/perfil.

    Equivale a ``GET /api/AutenticacaoSgp/CarregarDadosAcesso/
    usuarios/{login}/perfis/{perfil}``.

    O JWT enriquecido é gerado pelo SME-Identidade-Token-Microsserviço,
    que é responsável por buscar a projeção de autorização, compor as
    claims e assinar o token.

    O Gateway apenas solicita o token ao Token-MS e retorna o contexto
    de acesso ao cliente.
    """

    authentication_classes = [AutenticacaoApiKey]

    @extend_schema(
        responses=DadosAcessoResponseSerializer,
        tags=["Níveis de Acesso"],
    )
    def get(self, request: Request, login: str, perfil: str) -> Response:
        """Retorna o token enriquecido e as permissões reais do perfil.

        Args:
            request: Requisição HTTP recebida.
            login: RF, CPF ou login do usuário.
            perfil: Identificador do perfil selecionado.

        Returns:
            Token enriquecido e permissões associadas ao perfil; 204
            (sem corpo) se o login não existir no Keycloak ou não
            houver projeção para ele no Token-MS.
        """
        conta = _resolver_conta_keycloak(login)
        if not conta:
            return Response(status=204)

        try:
            with cliente_token_ms() as cliente:
                resposta = cliente.post(
                    f"/api/v1/token/enriquecido/{conta['kc_user_id']}/",
                    json={
                        **conta,
                        "perfil": perfil,
                    },
                )
        except httpx.TimeoutException:
            return Response({"erro": "token-ms timeout"}, status=504)
        except httpx.TransportError:
            return Response(_TOKEN_MS_INDISPONIVEL, status=502)

        if resposta.status_code == 404:
            return Response(status=204)
        if resposta.status_code != 200:
            return resposta_do_servico(resposta)

        dados_token = resposta.json()
        saida = DadosAcessoResponseSerializer(
            {
                "token": dados_token.get("token"),
                "data_expiracao_token": dados_token.get("data_expiracao"),
                "permissoes": dados_token.get(
                    "permissoes",
                    [],
                ),
            }
        )
        return Response(saida.data)
