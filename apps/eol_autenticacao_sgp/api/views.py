"""Views dos endpoints legados de autenticação do SGP."""

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autenticacao.api_key import AutenticacaoApiKey
from apps.autenticacao.keycloak_admin import ConsultaUsuariosKeycloak
from apps.autenticacao.services import (
    ConsultaUsuariosIndisponivelError,
    UsuarioNaoEncontradoError,
    existe_email_em_outro_usuario,
)
from apps.eol_autenticacao_sgp.api.serializers import (
    ErroConsultaUsuariosSerializer,
    ValidarEmailExistenteRequestSerializer,
)


class ValidarEmailExistenteView(APIView):
    """Consulta se o e-mail pertence a outra conta no realm de identidade."""

    authentication_classes = [AutenticacaoApiKey]
    permission_classes = [IsAuthenticated]
    @extend_schema(
        operation_id="sgp_validar_email_existente",
        parameters=[
            OpenApiParameter(
                "login",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                description="RF ou CPF da conta.",
            ),
            OpenApiParameter(
                "email",
                OpenApiTypes.EMAIL,
                OpenApiParameter.PATH,
                description="E-mail completo",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BOOL,
                description="True apenas quando outra conta possuir o e-mail.",
            ),
            400: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Parâmetros inválidos, com erros por campo.",
            ),
            401: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="API Key do gateway ausente ou inválida.",
            ),
            404: OpenApiResponse(
                response=ErroConsultaUsuariosSerializer,
                description="Login não encontrado no Keycloak.",
            ),
            502: OpenApiResponse(
                response=ErroConsultaUsuariosSerializer,
                description="Provedor de identidade indisponível.",
            ),
        },
        tags=["Autenticacao SGP"],
    )
    def get(self, request: Request, login: str, email: str) -> Response:
        """Valida a entrada e converte o resultado do serviço para HTTP.

        Reimplementa a rota
        `GET /api/AutenticacaoSgp/{login}/validarEmailExistente/{email}/`
        do legado.

        Args:
            request: Requisição HTTP do DRF.
            login: RF ou CPF do usuário que deve ser excluído da busca.
            email: E-mail completo a consultar.
        Returns:
            Response: True se outra conta possuir o e-mail;
        """
        entrada = ValidarEmailExistenteRequestSerializer(
            data={"login": login, "email": email}
        )
        entrada.is_valid(raise_exception=True)
        try:
            email_existe = existe_email_em_outro_usuario(
                login=entrada.validated_data["login"],
                email=entrada.validated_data["email"],
                usuarios=ConsultaUsuariosKeycloak(),
            )
        except UsuarioNaoEncontradoError as exc:
            return Response({"erro": str(exc)}, status=404)
        except ConsultaUsuariosIndisponivelError as exc:
            return Response({"erro": str(exc)}, status=502)

        return Response(email_existe)
