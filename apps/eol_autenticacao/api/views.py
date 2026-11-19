"""Views dos endpoints legados de autenticação."""

from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_field,
)
from rest_framework import serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autenticacao.api_key import AutenticacaoApiKey
from apps.eol_autenticacao import recuperacao_senha as recuperacao


@extend_schema_field({"type": "string", "example": ""})
class TextoSemValorInicial(serializers.CharField):
    """Campo obrigatório exibido sem preenchimento inicial no Swagger."""


class AlterarSenhaSerializer(serializers.Serializer):
    """Campos de formulário e mensagens exigidos pelo contrato legado."""

    Token = TextoSemValorInicial(
        help_text="Código de recuperação recebido no link enviado por e-mail.",
        trim_whitespace=False,
        error_messages={
            "required": (
                "É necessario informar o token de recuperação de senha"
            ),
            "blank": "É necessario informar o token de recuperação de senha",
        },
    )
    Senha = TextoSemValorInicial(
        help_text="Nova senha, com 8 a 12 caracteres, sem espaços.",
        trim_whitespace=False,
        write_only=True,
        error_messages={
            "required": "É necessario informar a nova senha",
            "blank": "É necessario informar a nova senha",
        },
    )


class JSONLegadoParser(JSONParser):
    """Aceita o media type usado pelo cliente .NET do Novo SGP."""

    media_type = "application/json-patch+json"


class RecuperacaoBaseView(APIView):
    """Converte erros de negócio em strings JSON como a API legada."""

    authentication_classes = [AutenticacaoApiKey]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, JSONLegadoParser]

    def handle_exception(self, exc: Exception) -> Response:
        """Adapta os erros da integração para o contrato público.

        Args:
            exc: Exceção levantada durante o processamento da requisição.

        Returns:
            Resposta com o status e a mensagem do adaptador do MS-Token,
            ou a resposta produzida pelo tratamento padrão do DRF.
        """
        if isinstance(exc, recuperacao.RecuperacaoSenhaError):
            return Response(str(exc), status=exc.status)
        return super().handle_exception(exc)


class RecuperarSenhaView(RecuperacaoBaseView):
    """Solicita recuperação pelo login (string JSON) e código do sistema."""

    @extend_schema(
        summary="Solicitar recuperação de senha",
        description=(
            "Envia ao e-mail cadastrado um link para redefinir a senha. O "
            "link vale por 6 horas e substitui a solicitação anterior. "
            "Retorna o e-mail de destino."
        ),
        request={"application/json": {"type": "string", "example": ""}},
        parameters=[
            OpenApiParameter(
                "sistema",
                int,
                required=True,
                description=(
                    "Código do sistema para o qual deseja recuperar a senha."
                ),
            )
        ],
        responses={200: {"type": "string"}},
        tags=["Autenticação"],
    )
    def post(self, request: Request) -> Response:
        """Solicita a recuperação e retorna o e-mail informado pelo MS-Token.

        Args:
            request: Requisição com o login como string JSON e o código
                do sistema na query string.

        Returns:
            E-mail de destino como string JSON, ou erro 400 quando o
            formato do login ou do código do sistema for inválido.
        """
        if not isinstance(request.data, str) or not request.data.strip():
            return Response("É necessario informar o login", status=400)
        try:
            sistema = int(request.query_params.get("sistema", 0))
        except (TypeError, ValueError):
            return Response("O sistema informado é inválido", status=400)
        return Response(recuperacao.solicitar(request.data, sistema))


class ValidarTokenView(RecuperacaoBaseView):
    """Consulta o UUID sem consumi-lo, retornando um booleano JSON."""

    @extend_schema(
        summary="Verificar código de recuperação de senha",
        description=(
            "Informa se o código de recuperação ainda pode ser usado. Retorna "
            "`false` para código inexistente, expirado ou já utilizado. A "
            "consulta não consome o código."
        ),
        request={
            "application/json": {
                "type": "string",
                "format": "uuid",
                "example": "",
            }
        },
        responses={200: {"type": "boolean"}},
        tags=["Autenticação"],
    )
    def post(self, request: Request) -> Response:
        """Verifica o formato do UUID e consulta sua validade no MS-Token.

        Args:
            request: Requisição com o UUID como string JSON.

        Returns:
            Booleano JSON informado pelo MS-Token, ou erro 400 quando o
            corpo não contiver um UUID em formato válido.
        """
        if (
            not isinstance(request.data, str)
            or not recuperacao.normalizar_uuid(request.data)
        ):
            return Response("O token informado é inválido", status=400)
        return Response(recuperacao.validar(request.data))


class AlterarSenhaView(RecuperacaoBaseView):
    """Altera a senha apenas com token válido recebido via formulário."""

    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Definir nova senha com código de recuperação",
        description=(
            "Define a nova senha e invalida o código de recuperação após a "
            "troca. A senha deve ter de 8 a 12 caracteres, sem espaços, com "
            "letras maiúsculas, minúsculas e um número ou caractere especial. "
            "Senhas padrão e as últimas cinco senhas não são aceitas. Retorna "
            "o login do usuário."
        ),
        request=AlterarSenhaSerializer,
        responses={200: {"type": "string"}, 401: {"type": "string"}},
        tags=["Autenticação"],
    )
    def post(self, request: Request) -> Response:
        """Encaminha o formulário legado para a troca de senha no MS-Token.

        Os nomes dos campos são lidos sem diferenciar maiúsculas de
        minúsculas, preservando o binding do contrato ASP.NET.

        Args:
            request: Requisição de formulário com os campos Token e Senha.

        Returns:
            Login como string JSON após a troca, ou erro 400 quando o
            corpo não tiver formato de formulário.

        Raises:
            rest_framework.exceptions.ValidationError: Se Token ou Senha
                estiverem ausentes ou vazios.
        """
        if not isinstance(request.data, dict):
            return Response("Formato de solicitação inválido.", status=400)
        dados = {chave.lower(): request.data[chave] for chave in request.data}
        entrada = AlterarSenhaSerializer(
            data={
                chave: dados[chave.lower()]
                for chave in ("Token", "Senha")
                if chave.lower() in dados
            }
        )
        entrada.is_valid(raise_exception=True)
        login = recuperacao.alterar(
            entrada.validated_data["Token"],
            entrada.validated_data["Senha"],
        )
        return Response(login)
