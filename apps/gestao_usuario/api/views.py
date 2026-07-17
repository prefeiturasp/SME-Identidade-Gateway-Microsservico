"""Views do domínio de gestão de usuário.

Camada fina de entrada: autentica a requisição do cliente externo
via ``AutenticacaoApiKey``, valida o payload com os serializers
locais e repassa para o SME-Identidade-ETL — que é quem de fato fala
com o Keycloak Admin API. Nenhuma lógica de upsert, idempotência ou
provisionamento é reimplementada aqui.
"""

from __future__ import annotations

import httpx
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autenticacao.api_key import AutenticacaoApiKey
from apps.gestao_usuario.api.serializers import (
    ConcederAcessoSerializer,
    CriarUsuarioSerializer,
    RespostaGenericaSerializer,
    SincronizarUsuarioSerializer,
)
from apps.gestao_usuario.cliente_etl import cliente_etl

_ETL_INDISPONIVEL = {"erro": "etl indisponível"}


def _resposta_do_etl(resposta: httpx.Response) -> Response:
    """Monta a ``Response`` a partir da resposta do ETL.

    O ETL fica atrás de proxies/WAF que podem responder com uma
    página de erro HTML (ex.: 404 de infraestrutura) em vez do JSON
    esperado — nesse caso ``resposta.json()`` lançaria
    ``JSONDecodeError`` sem ser capturado, derrubando a view com 500
    em vez de repassar um erro tratável ao cliente.
    """
    if not resposta.content:
        return Response(None, status=resposta.status_code)
    try:
        return Response(resposta.json(), status=resposta.status_code)
    except ValueError:
        return Response(
            {
                "erro": "resposta inválida do etl",
                "status_etl": resposta.status_code,
            },
            status=502,
        )


class CriarUsuarioView(APIView):
    """Cria um usuário no Keycloak a partir de dados diretos.

    Repassa para ``POST /identidade-etl/api/v1/etl/usuario/criar/``.
    Não depende do usuário já existir no CoreSSO.
    """

    authentication_classes = [AutenticacaoApiKey]

    @extend_schema(
        request=CriarUsuarioSerializer,
        responses=RespostaGenericaSerializer,
        tags=["Gestão de Usuário"],
    )
    def post(self, request: Request) -> Response:
        """Valida o payload e repassa a criação ao ETL.

        Args:
            request: Requisição HTTP com os dados do usuário.

        Returns:
            Resposta do ETL repassada como veio, ou erro de
            comunicação (504/502).
        """
        entrada = CriarUsuarioSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        try:
            with cliente_etl() as cliente:
                resposta = cliente.post(
                    "/api/v1/etl/usuario/criar/",
                    json=entrada.validated_data,
                )
        except httpx.TimeoutException:
            return Response({"erro": "etl timeout"}, status=504)
        except httpx.TransportError:
            return Response(_ETL_INDISPONIVEL, status=502)

        return _resposta_do_etl(resposta)


class SincronizarUsuarioView(APIView):
    """Sincroniza um usuário existente no CoreSSO com o Keycloak.

    Repassa para
    ``POST /identidade-etl/api/v1/etl/usuario/sincronizar/``.
    """

    authentication_classes = [AutenticacaoApiKey]

    @extend_schema(
        request=SincronizarUsuarioSerializer,
        responses=RespostaGenericaSerializer,
        tags=["Gestão de Usuário"],
    )
    def post(self, request: Request) -> Response:
        """Valida o payload e repassa a sincronização ao ETL.

        Args:
            request: Requisição HTTP com o identificador do usuário.

        Returns:
            Resposta do ETL repassada como veio, ou erro de
            comunicação (504/502).
        """
        entrada = SincronizarUsuarioSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        try:
            with cliente_etl() as cliente:
                resposta = cliente.post(
                    "/api/v1/etl/usuario/sincronizar/",
                    json=entrada.validated_data,
                )
        except httpx.TimeoutException:
            return Response({"erro": "etl timeout"}, status=504)
        except httpx.TransportError:
            return Response(_ETL_INDISPONIVEL, status=502)

        return _resposta_do_etl(resposta)


class ConcederAcessoView(APIView):
    """Concede acesso a um sistema e roles no Keycloak.

    Repassa para
    ``POST /identidade-etl/api/v1/etl/usuario/conceder-acesso/``.
    """

    authentication_classes = [AutenticacaoApiKey]

    @extend_schema(
        request=ConcederAcessoSerializer,
        responses=RespostaGenericaSerializer,
        tags=["Gestão de Usuário"],
    )
    def post(self, request: Request) -> Response:
        """Valida o payload e repassa a concessão de acesso ao ETL.

        Args:
            request: Requisição HTTP com identificador, sistema e
                roles a conceder.

        Returns:
            Resposta do ETL repassada como veio, ou erro de
            comunicação (504/502).
        """
        entrada = ConcederAcessoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        try:
            with cliente_etl() as cliente:
                resposta = cliente.post(
                    "/api/v1/etl/usuario/conceder-acesso/",
                    json=entrada.validated_data,
                )
        except httpx.TimeoutException:
            return Response({"erro": "etl timeout"}, status=504)
        except httpx.TransportError:
            return Response(_ETL_INDISPONIVEL, status=502)

        return _resposta_do_etl(resposta)


class ConsultarIdentidadeView(APIView):
    """Consulta a conta do usuário diretamente no Keycloak.

    Repassa para
    ``GET /identidade-etl/api/v1/etl/identidades/consultar/``, que
    busca via Keycloak Admin API (não é cache local) — reflete o
    estado real, independentemente de qual rota criou o usuário.
    Exige ``AutenticacaoApiKey``, já que cada consulta gera uma
    chamada real ao Keycloak.
    """

    authentication_classes = [AutenticacaoApiKey]

    @extend_schema(
        parameters=[
            OpenApiParameter("cpf", str, required=False),
            OpenApiParameter("rf", str, required=False),
            OpenApiParameter("email", str, required=False),
            OpenApiParameter("realm", str, required=False),
        ],
        responses=RespostaGenericaSerializer,
        tags=["Gestão de Usuário"],
    )
    def get(self, request: Request) -> Response:
        """Repassa a consulta de identidade ao ETL.

        Args:
            request: Requisição HTTP com filtros via querystring
                (``cpf``, ``rf``, ``email``, ``realm``).

        Returns:
            Resposta do ETL repassada como veio, ou erro de
            comunicação (504/502).
        """
        try:
            with cliente_etl() as cliente:
                resposta = cliente.get(
                    "/api/v1/etl/identidades/consultar/",
                    params=request.GET,
                )
        except httpx.TimeoutException:
            return Response({"erro": "etl timeout"}, status=504)
        except httpx.TransportError:
            return Response(_ETL_INDISPONIVEL, status=502)

        return _resposta_do_etl(resposta)
