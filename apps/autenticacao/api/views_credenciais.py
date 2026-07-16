"""Views de gestão de credencial (senha e e-mail).

Diferente das views em ``views.py`` (login e níveis de acesso, hoje
mockadas aguardando o token-ms), estas views já operam de verdade
contra o Keycloak — gestão de credencial é responsabilidade nativa
do Keycloak, então não há razão para mockar: delegamos diretamente
via ``apps.autenticacao.keycloak_admin``.

Nenhuma destas views gera, armazena ou valida token de recuperação
de senha — isso é feito inteiramente pelo Keycloak.
"""

from drf_spectacular.utils import extend_schema
from keycloak.exceptions import KeycloakGetError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autenticacao import keycloak_admin
from apps.autenticacao.api.serializers import (
    AlterarEmailRequestSerializer,
    AlterarSenhaRequestSerializer,
    OperacaoConfirmadaResponseSerializer,
    RecuperarSenhaRequestSerializer,
)
from apps.autenticacao.api_key import AutenticacaoApiKey
from apps.autenticacao.keycloak_admin import ERRO_USUARIO_NAO_ENCONTRADO


class RecuperarSenhaView(APIView):
    """Dispara a recuperação de senha nativa do Keycloak.

    Equivale a
    ``POST /api/v1/autenticacao/RecuperarSenha/usuario``.
    """

    authentication_classes = [AutenticacaoApiKey]

    @extend_schema(
        request=RecuperarSenhaRequestSerializer,
        responses=OperacaoConfirmadaResponseSerializer,
        tags=["Gestão de Credencial"],
    )
    def post(self, request: Request) -> Response:
        """Solicita o envio do e-mail de redefinição de senha.

        Args:
            request: Requisição HTTP com o ``login`` do usuário.

        Returns:
            Confirmação de que a solicitação foi encaminhada ao
            Keycloak, ou 404 se o login não existir.
        """
        entrada = RecuperarSenhaRequestSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        try:
            keycloak_admin.disparar_redefinicao_senha(
                entrada.validated_data["login"]
            )
        except KeycloakGetError:
            return Response({"erro": ERRO_USUARIO_NAO_ENCONTRADO}, status=404)

        saida = OperacaoConfirmadaResponseSerializer(
            {"situacao": "solicitacao_enviada"}
        )
        return Response(saida.data)


class AlterarSenhaView(APIView):
    """Redefine a senha do usuário como temporária no Keycloak.

    Equivale a ``POST /api/AutenticacaoSgp/AlterarSenha``. A senha
    definida exige troca no próximo login (``temporary=True``).
    """

    authentication_classes = [AutenticacaoApiKey]

    @extend_schema(
        request=AlterarSenhaRequestSerializer,
        responses=OperacaoConfirmadaResponseSerializer,
        tags=["Gestão de Credencial"],
    )
    def post(self, request: Request) -> Response:
        """Define uma senha temporária para o usuário.

        Args:
            request: Requisição HTTP com ``login`` e ``senha``.

        Returns:
            Confirmação da alteração, ou 404 se o login não existir.
        """
        entrada = AlterarSenhaRequestSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        try:
            keycloak_admin.redefinir_senha_temporaria(
                entrada.validated_data["login"],
                entrada.validated_data["senha"],
            )
        except KeycloakGetError:
            return Response({"erro": ERRO_USUARIO_NAO_ENCONTRADO}, status=404)

        saida = OperacaoConfirmadaResponseSerializer(
            {"situacao": "senha_alterada"}
        )
        return Response(saida.data)


class AlterarEmailView(APIView):
    """Atualiza o e-mail do usuário e reabre a verificação.

    Equivale a ``POST /api/AutenticacaoSgp/AlterarEmail``.
    """

    authentication_classes = [AutenticacaoApiKey]

    @extend_schema(
        request=AlterarEmailRequestSerializer,
        responses=OperacaoConfirmadaResponseSerializer,
        tags=["Gestão de Credencial"],
    )
    def post(self, request: Request) -> Response:
        """Atualiza o e-mail e dispara a verificação no Keycloak.

        Args:
            request: Requisição HTTP com ``login`` e ``email``.

        Returns:
            Confirmação da alteração, ou 404 se o login não existir.
        """
        entrada = AlterarEmailRequestSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        try:
            keycloak_admin.alterar_email(
                entrada.validated_data["login"],
                entrada.validated_data["email"],
            )
        except KeycloakGetError:
            return Response({"erro": ERRO_USUARIO_NAO_ENCONTRADO}, status=404)

        saida = OperacaoConfirmadaResponseSerializer(
            {"situacao": "email_alterado"}
        )
        return Response(saida.data)
