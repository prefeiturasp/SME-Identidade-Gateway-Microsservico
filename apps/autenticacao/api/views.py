"""Views do fluxo de login e níveis de acesso.

Endpoints de entrada do Gateway para o domínio de autenticação e
autorização. Todas consultam serviços reais: ``LoginView`` e
``DadosUsuarioView`` falam com o Keycloak (via
``apps.autenticacao.keycloak_admin``, mesmo padrão do comando
``validar_login`` do SME-Identidade-ETL); ``LoginView``,
``PerfisPorLoginView`` e ``DadosAcessoView`` também consultam a
projeção de autorização no SME-Identidade-Token-Microsservico (via
``apps.core.clientes.token_ms``) e compõem o token enriquecido (via
``apps.autenticacao.token_enriquecido``) — o Gateway é o próprio
auth-gateway-ms da arquitetura normativa da plataforma.

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
    PerfisPorLoginResponseSerializer,
)
from apps.autenticacao.api_key import AutenticacaoApiKey
from apps.autenticacao.keycloak_admin import ERRO_USUARIO_NAO_ENCONTRADO
from apps.autenticacao.token_enriquecido import compor_token_enriquecido
from apps.core.clientes.token_ms import cliente_token_ms
from apps.core.http import resposta_do_servico

_TOKEN_MS_INDISPONIVEL = {"erro": "token-ms indisponível"}


def _buscar_projecao_token_ms(kc_user_id: str) -> dict | None:
    """Busca a projeção de autorização do usuário no Token-MS.

    Usada tanto no login quanto nas consultas avulsas de
    perfis/acesso — a ausência de projeção (``404``) ou uma falha de
    comunicação não são tratadas como erro aqui: o chamador decide
    se isso deve bloquear a operação (rotas de consulta avulsa,
    ``204``) ou apenas resultar em claims vazias (login, que não deve
    falhar por uma dependência complementar estar fora do ar).

    Args:
        kc_user_id: UUID do usuário no Keycloak.

    Returns:
        O corpo da projeção, ou ``None`` se não houver projeção ou o
        Token-MS não puder ser consultado.
    """
    try:
        with cliente_token_ms() as cliente:
            resposta = cliente.get(f"/api/v1/perfis/{kc_user_id}/")
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
        brutos do Keycloak, busca a projeção no Token-MS e compõe o
        token enriquecido — sem exigir uma segunda requisição a
        ``DadosAcessoView``. Ausência de projeção no Token-MS (ou o
        serviço fora do ar) não bloqueia o login, já a autenticação
        no Keycloak é o que importa: as claims de ``perfis``/
        ``permissoes`` dentro do token enriquecido ficam vazias nesse
        caso.

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

        projecao = _buscar_projecao_token_ms(resultado["kc_user_id"])
        token_enriquecido, expiracao = compor_token_enriquecido(
            resultado, projecao
        )
        resultado["token_enriquecido"] = token_enriquecido
        resultado["data_expiracao_token_enriquecido"] = expiracao

        saida = LoginResponseSerializer(resultado)
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
    lugar — o formato retornado já é o esperado por
    ``compor_token_enriquecido``.

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
    usuarios/{login}/perfis/{perfil}``. ``permissoes`` vem da
    projeção real no SME-Identidade-Token-Microsservico. O ``token``
    é o JWT enriquecido, composto pelo próprio Gateway (auth-gateway-ms)
    a partir das claims do Keycloak e da projeção do Token-MS — ver
    ``apps.autenticacao.token_enriquecido``.
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
        token, expiracao = compor_token_enriquecido(conta, projecao, perfil)
        saida = DadosAcessoResponseSerializer(
            {
                "token": token,
                "data_expiracao_token": expiracao,
                "permissoes": projecao.get("permissoes", []),
            }
        )
        return Response(saida.data)
