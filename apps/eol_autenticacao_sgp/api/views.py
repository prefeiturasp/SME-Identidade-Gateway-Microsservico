"""Views dos endpoints legados de autenticação do SGP."""

import logging

from drf_spectacular.utils import (
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autenticacao.api_key import AutenticacaoApiKey
from apps.eol_autenticacao_sgp.api.serializers import DadosUsuarioSerializer
from apps.eol_autenticacao_sgp.services import (
    ServicoDadosUsuario,
)

logger = logging.getLogger(__name__)

_ERRO_SQL = (
    "Houve um problema na conexão com o banco do EOL. "
    "Por favor, contate a SME."
)

_ERRO_GERAL = (
    "Houve um comportamento inesperado do sistema. "
    "Por favor, contate a SME."
)


class DadosUsuarioView(APIView):
    """Disponibiliza a consulta de dados cadastrais do usuário."""

    authentication_classes = [AutenticacaoApiKey]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Consulta os dados cadastrais de um usuário",
        responses={
            200: DadosUsuarioSerializer,
            204: OpenApiResponse(
                description="Dados do usuário não encontrados.",
            ),
            400: OpenApiResponse(
                response=OpenApiTypes.STR,
                description="Falha na consulta dos dados.",
            ),
            401: OpenApiResponse(
                description="API Key ausente ou inválida.",
            ),
        },
        tags=["Autenticação SGP"],
    )
    def get(self, request: Request, login: str) -> Response:
        """Consulta os dados cadastrais do usuário pelo login.

        Args:
            request: Requisição HTTP recebida.
            login: Login do usuário.

        Returns:
            Resposta HTTP com os dados ou o status correspondente.
        """
        servico = ServicoDadosUsuario()

        try:
            dados = servico.carregar(login)

        except Exception:
            logger.exception("Falha ao consultar os dados do usuário.")
            return Response(_ERRO_GERAL, status=400)

        if dados is None:
            return Response(status=204)

        serializer = DadosUsuarioSerializer(dados)
        return Response(serializer.data, status=200)
