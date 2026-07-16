"""Views do fluxo de login e níveis de acesso.

Endpoints de entrada do Gateway para o domínio de autenticação e
autorização. ``LoginView`` e ``DadosUsuarioView`` já autenticam e
consultam de verdade contra o Keycloak (via
``apps.autenticacao.keycloak_admin``, mesmo padrão do comando
``validar_login`` do SME-Identidade-ETL). ``PerfisPorLoginView`` e
``DadosAcessoView`` seguem mockadas — o
SME-Identidade-Token-Microsservico, que fornecerá os dados reais de
perfil e abrangência, ainda está em desenvolvimento por outro time.

Todas as views exigem autenticação via ``AutenticacaoApiKey``, no
mesmo padrão usado pelo SME-Identidade-ETL e esperado no
SME-Identidade-Token-Microsservico.
"""

import uuid
from datetime import UTC, datetime, timedelta

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

        Args:
            request: Requisição HTTP com ``login`` e ``senha``.

        Returns:
            Identidade autenticada + tokens, ou 401/404 conforme o
            resultado da autenticação.
        """
        entrada = LoginRequestSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        resultado = keycloak_admin.autenticar(
            entrada.validated_data["login"],
            entrada.validated_data["senha"],
        )
        if not resultado["autenticado"]:
            status_code = (
                404
                if resultado.get("erro") == "usuário não encontrado"
                else 401
            )
            return Response({"detalhe": resultado["erro"]}, status=status_code)

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
            Dados cadastrais do usuário, ou 404 se não encontrado.
        """
        dados = keycloak_admin.obter_dados_usuario(login)
        if not dados:
            return Response({"detalhe": "usuário não encontrado"}, status=404)

        saida = DadosUsuarioResponseSerializer(dados)
        return Response(saida.data)


class PerfisPorLoginView(APIView):
    """Retorna os perfis de acesso de um usuário.

    Equivale a
    ``GET /api/AutenticacaoSgp/CarregarPerfisPorLogin/{login}``.
    Quando o token-ms estiver disponível, esta view passa a
    consultá-lo em vez de retornar o mock abaixo.
    """

    authentication_classes = [AutenticacaoApiKey]

    @extend_schema(
        responses=PerfisPorLoginResponseSerializer,
        tags=["Níveis de Acesso"],
    )
    def get(self, request: Request, login: str) -> Response:
        """Retorna os perfis de acesso vinculados ao login (mock).

        Args:
            request: Requisição HTTP recebida.
            login: RF, CPF ou login do usuário.

        Returns:
            Lista de perfis de acesso do usuário.
        """
        saida = PerfisPorLoginResponseSerializer(
            {
                "rf": login,
                "perfis": [
                    {
                        "id": uuid.uuid4(),
                        "nome": "professor",
                        "ativo": True,
                    },
                ],
            }
        )
        return Response(saida.data)


class DadosAcessoView(APIView):
    """Retorna o contexto de acesso completo de um usuário/perfil.

    Equivale a ``GET /api/AutenticacaoSgp/CarregarDadosAcesso/
    usuarios/{login}/perfis/{perfil}``. O ``token`` retornado é o
    JWT enriquecido — composto pelo auth-gateway-ms, não emitido
    pelo token-ms.
    """

    authentication_classes = [AutenticacaoApiKey]

    @extend_schema(
        responses=DadosAcessoResponseSerializer,
        tags=["Níveis de Acesso"],
    )
    def get(self, request: Request, login: str, perfil: str) -> Response:
        """Retorna token enriquecido e permissões do perfil (mock).

        Args:
            request: Requisição HTTP recebida.
            login: RF, CPF ou login do usuário.
            perfil: Identificador do perfil selecionado.

        Returns:
            Token enriquecido e permissões associadas ao perfil.
        """
        expiracao = datetime.now(UTC) + timedelta(hours=8)
        saida = DadosAcessoResponseSerializer(
            {
                "token": "mock.jwt.token",
                "data_expiracao_token": expiracao,
                "permissoes": [
                    {"codigo": 1, "descricao": "acesso_basico"},
                ],
            }
        )
        return Response(saida.data)
