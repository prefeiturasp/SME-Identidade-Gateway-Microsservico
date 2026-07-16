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
                    "/identidade-etl/api/v1/etl/usuario/criar/",
                    json=entrada.validated_data,
                )
        except httpx.TimeoutException:
            return Response({"erro": "etl timeout"}, status=504)
        except httpx.TransportError:
            return Response(_ETL_INDISPONIVEL, status=502)

        return Response(
            resposta.json() if resposta.content else None,
            status=resposta.status_code,
        )


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
                    "/identidade-etl/api/v1/etl/usuario/sincronizar/",
                    json=entrada.validated_data,
                )
        except httpx.TimeoutException:
            return Response({"erro": "etl timeout"}, status=504)
        except httpx.TransportError:
            return Response(_ETL_INDISPONIVEL, status=502)

        return Response(
            resposta.json() if resposta.content else None,
            status=resposta.status_code,
        )


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
                    "/identidade-etl/api/v1/etl/usuario/conceder-acesso/",
                    json=entrada.validated_data,
                )
        except httpx.TimeoutException:
            return Response({"erro": "etl timeout"}, status=504)
        except httpx.TransportError:
            return Response(_ETL_INDISPONIVEL, status=502)

        return Response(
            resposta.json() if resposta.content else None,
            status=resposta.status_code,
        )


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
                    "/identidade-etl/api/v1/etl/identidades/consultar/",
                    params=request.GET,
                )
        except httpx.TimeoutException:
            return Response({"erro": "etl timeout"}, status=504)
        except httpx.TransportError:
            return Response(_ETL_INDISPONIVEL, status=502)

        return Response(
            resposta.json() if resposta.content else None,
            status=resposta.status_code,
        )
