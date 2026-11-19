"""Views dos endpoints legados de autenticação EOL."""

import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autenticacao.api_key import AutenticacaoApiKey
from apps.eol_autenticacao.api.serializers import (
    AutenticacaoExternaRequestSerializer,
    RetornoUsuarioExternoSerializer,
)
from apps.eol_autenticacao.services import (
    CodigoSistemaInvalidoError,
    CredenciaisExternasInvalidasError,
    ServicoAutenticacaoExterna,
    UsuarioExternoNaoEncontradoError,
)

logger = logging.getLogger(__name__)

_ERRO_GERAL = (
    "Houve um comportamento inesperado do sistema. "
    "Por favor, contate a SME."
)


class AutenticacaoExternaView(APIView):
    """Autentica usuários externos e devolve o contrato da API legada."""

    authentication_classes = [AutenticacaoApiKey]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Autentica usuário externo no Keycloak",
        request=AutenticacaoExternaRequestSerializer,
        responses={
            200: RetornoUsuarioExternoSerializer,
            400: OpenApiResponse(response=OpenApiTypes.STR),
            401: OpenApiResponse(response=OpenApiTypes.STR),
            601: OpenApiResponse(response=OpenApiTypes.STR),
        },
        tags=["Autenticação EOL"],
    )
    def post(self, request: Request) -> Response:
        """Autentica o usuário e devolve os dez campos do DTO legado.

        Args:
            request: Requisição com usuário, senha e código do sistema.

        Returns:
            Resposta com os dados do usuário em caso de sucesso, ou
            mensagem de erro no formato esperado pelo Legado.

        Raises:
            ValidationError: Se os dados de entrada forem inválidos.
        """
        entrada = AutenticacaoExternaRequestSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        try:
            dados = ServicoAutenticacaoExterna().autenticar(
                usuario=entrada.validated_data["usuario"],
                senha=entrada.validated_data["senha"],
                codigo_sistema=entrada.validated_data["codigoSistema"],
            )
        except CodigoSistemaInvalidoError as exc:
            resposta = Response(str(exc), status=400)
            resposta.status_code = 601
            return resposta
        except (
            UsuarioExternoNaoEncontradoError,
            CredenciaisExternasInvalidasError,
        ) as exc:
            return Response(str(exc), status=401)
        except Exception:
            logger.exception("Falha na autenticação externa do EOL.")
            return Response(_ERRO_GERAL, status=400)

        serializer = RetornoUsuarioExternoSerializer(dados)
        return Response(serializer.data, status=200)
