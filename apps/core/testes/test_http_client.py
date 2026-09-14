"""Testes do cliente HTTP compartilhado."""

from unittest.mock import MagicMock, patch

import httpx
from django.conf import settings
from django.test import SimpleTestCase
from sme_sidecar_sdk import CircuitOpenError, build_http_client
from sme_sidecar_sdk.observability.context import correlation_context

from apps.core.apps import CoreConfig
from apps.core.http_client import ServiceClient


def _make_token_client(
    *,
    api_key: str = "",
    api_key_header: str = "X-API-Key",
) -> ServiceClient:
    """Cria um ServiceClient fictício para o domínio token."""
    return ServiceClient(
        base_url="https://token-ms",
        dominio="token",
        api_key=api_key,
        api_key_header=api_key_header,
    )


def _make_auditoria_client(
    *,
    api_key: str = "",
    api_key_header: str = "X-API-Key",
) -> ServiceClient:
    """Cria um ServiceClient fictício para o domínio auditoria."""
    return ServiceClient(
        base_url="https://auditoria-ms",
        dominio="auditoria",
        api_key=api_key,
        api_key_header=api_key_header,
    )


class SidecarIntegracaoTest(SimpleTestCase):
    """Valida a integração da aplicação com o SME Sidecar SDK."""

    @patch("sme_sidecar_sdk.runtime.configure")
    def test_inicializa_sidecar_no_boot(
        self,
        mock_configure: MagicMock,
    ) -> None:
        """Deve configurar o Sidecar ao inicializar a app core."""
        config = CoreConfig(
            "apps.core",
            __import__("apps.core"),
        )

        config.ready()

        mock_configure.assert_called_once()

        configuracao = mock_configure.call_args.args[0]

        self.assertEqual(
            configuracao.service_name,
            "gateway-auth-ms",
        )

        self.assertEqual(
            configuracao.service_version,
            "0.0.1",
        )

    def test_middleware_observabilidade_esta_configurado(
        self,
    ) -> None:
        """Deve registrar o middleware de observabilidade da SDK."""
        self.assertIn(
            "sme_sidecar_sdk.integrations.django.ObservabilityMiddleware",
            settings.MIDDLEWARE,
        )


class ServiceClientConfigurationTest(SimpleTestCase):
    """Valida a configuração do ServiceClient."""

    def test_remove_barra_final_da_base_url(self) -> None:
        """Deve normalizar a URL base."""
        svc = ServiceClient(
            base_url="https://token-ms/",
            dominio="token",
        )

        self.assertEqual(
            svc.base_url,
            "https://token-ms",
        )

    def test_headers_sem_api_key(self) -> None:
        """Deve enviar somente Accept sem API Key."""
        svc = _make_token_client()

        self.assertEqual(
            svc._headers(),  # noqa: SLF001
            {
                "Accept": "application/json",
            },
        )

    def test_headers_com_api_key(self) -> None:
        """Deve incluir a API Key configurada."""
        svc = _make_token_client(
            api_key="chave-token",
            api_key_header="X-API-Key",
        )

        self.assertEqual(
            svc._headers(),  # noqa: SLF001
            {
                "Accept": "application/json",
                "X-API-Key": "chave-token",
            },
        )


class ServiceClientRequestTest(SimpleTestCase):
    """Valida a delegação das chamadas HTTP ao Sidecar."""

    @patch("apps.core.http_client.build_http_client")
    def test_cria_cliente_token_somente_na_primeira_chamada(
        self,
        mock_build_http_client: MagicMock,
    ) -> None:
        """Deve criar o cliente de forma preguiçosa."""
        svc = _make_token_client()

        mock_build_http_client.assert_not_called()

        svc.get("/api/v1/health/")

        mock_build_http_client.assert_called_once_with(
            "token",
            base_url="https://token-ms",
            follow_redirects=True,
        )

    @patch("apps.core.http_client.build_http_client")
    def test_reaproveita_cliente_token_em_gets(
        self,
        mock_build_http_client: MagicMock,
    ) -> None:
        """Deve reutilizar o cliente Sidecar nas chamadas GET."""
        svc = _make_token_client()

        svc.get("/api/v1/health/")
        svc.get("/api/v1/perfis/123/")

        mock_build_http_client.assert_called_once_with(
            "token",
            base_url="https://token-ms",
            follow_redirects=True,
        )

        cliente = mock_build_http_client.return_value

        self.assertEqual(
            cliente.get.call_count,
            2,
        )

        cliente.get.assert_any_call(
            "/api/v1/health/",
            headers={
                "Accept": "application/json",
            },
            params=None,
        )

        cliente.get.assert_any_call(
            "/api/v1/perfis/123/",
            headers={
                "Accept": "application/json",
            },
            params=None,
        )

    @patch("apps.core.http_client.build_http_client")
    def test_get_repassa_headers_e_params(
        self,
        mock_build_http_client: MagicMock,
    ) -> None:
        """Deve repassar GET e preservar resposta de erro HTTP."""
        svc = _make_token_client(
            api_key="chave-token",
        )

        params = {"ativo": True}

        request = httpx.Request(
            "GET",
            "https://token-ms/api/v1/perfis/123/",
        )
        response = httpx.Response(
            404,
            request=request,
        )

        mock_build_http_client.return_value.get.side_effect = (
            httpx.HTTPStatusError(
                "Not Found",
                request=request,
                response=response,
            )
        )

        resultado = svc.get(
            "/api/v1/perfis/123/",
            params=params,
        )

        self.assertIs(resultado, response)

        mock_build_http_client.return_value.get.assert_called_once_with(
            "/api/v1/perfis/123/",
            headers={
                "Accept": "application/json",
                "X-API-Key": "chave-token",
            },
            params=params,
        )

    @patch("apps.core.http_client.build_http_client")
    def test_post_token_repassa_payload(
        self,
        mock_build_http_client: MagicMock,
    ) -> None:
        """Deve repassar payload e preservar resposta de erro HTTP."""
        svc = _make_token_client(
            api_key="chave-token",
        )

        payload = {
            "perfil": "professor",
        }

        request = httpx.Request(
            "POST",
            "https://token-ms/api/v1/token/enriquecido/123/",
        )
        response = httpx.Response(
            400,
            request=request,
        )

        mock_build_http_client.return_value.post.side_effect = (
            httpx.HTTPStatusError(
                "Bad Request",
                request=request,
                response=response,
            )
        )

        resultado = svc.post(
            "/api/v1/token/enriquecido/123/",
            payload=payload,
        )

        self.assertIs(resultado, response)

        mock_build_http_client.return_value.post.assert_called_once_with(
            "/api/v1/token/enriquecido/123/",
            headers={
                "Accept": "application/json",
                "X-API-Key": "chave-token",
            },
            json=payload,
            params=None,
        )

    @patch("apps.core.http_client.build_http_client")
    def test_post_auditoria_repassa_payload(
        self,
        mock_build_http_client: MagicMock,
    ) -> None:
        """Deve repassar o payload para o serviço de auditoria."""
        svc = _make_auditoria_client(
            api_key="chave-auditoria",
        )

        payload = {
            "realm": "COTIC",
            "usuario_id": "123",
        }

        svc.post(
            "/api/v1/gatilho-poll/",
            payload=payload,
        )

        mock_build_http_client.return_value.post.assert_called_once_with(
            "/api/v1/gatilho-poll/",
            headers={
                "Accept": "application/json",
                "X-API-Key": "chave-auditoria",
            },
            json=payload,
            params=None,
        )

    @patch("apps.core.http_client.build_http_client")
    def test_put_repassa_payload(
        self,
        mock_build_http_client: MagicMock,
    ) -> None:
        """Deve delegar PUT e preservar resposta de erro HTTP."""
        svc = _make_token_client(
            api_key="chave-token",
        )

        payload = {
            "perfil": "professor",
        }

        request = httpx.Request(
            "PUT",
            "https://token-ms/api/v1/token/123/",
        )
        response = httpx.Response(
            400,
            request=request,
        )

        mock_build_http_client.return_value.put.side_effect = (
            httpx.HTTPStatusError(
                "Bad Request",
                request=request,
                response=response,
            )
        )

        resultado = svc.put(
            "/api/v1/token/123/",
            payload=payload,
        )

        self.assertIs(resultado, response)

        mock_build_http_client.return_value.put.assert_called_once_with(
            "/api/v1/token/123/",
            headers={
                "Accept": "application/json",
                "X-API-Key": "chave-token",
            },
            json=payload,
            params=None,
        )


class ServiceClientLifecycleTest(SimpleTestCase):
    """Valida o fechamento do cliente HTTP."""

    @patch("apps.core.http_client.build_http_client")
    def test_close_fecha_cliente_http(
        self,
        mock_build_http_client: MagicMock,
    ) -> None:
        """Deve fechar o cliente já criado."""
        svc = _make_token_client()

        svc.get("/api/v1/health/")
        svc.close()

        mock_build_http_client.return_value.close.assert_called_once_with()

    @patch("apps.core.http_client.build_http_client")
    def test_close_permite_criar_novo_cliente(
        self,
        mock_build_http_client: MagicMock,
    ) -> None:
        """Deve recriar o cliente após close."""
        svc = _make_token_client()

        svc.get("/api/v1/health/")
        svc.close()
        svc.get("/api/v1/health/")

        self.assertEqual(
            mock_build_http_client.call_count,
            2,
        )

    @patch("apps.core.http_client.build_http_client")
    def test_close_sem_cliente_nao_cria_cliente(
        self,
        mock_build_http_client: MagicMock,
    ) -> None:
        """Não deve criar cliente apenas para executar close."""
        svc = _make_token_client()

        svc.close()

        mock_build_http_client.assert_not_called()


class ServiceClientCircuitBreakerTest(SimpleTestCase):
    """Valida a conversão do circuito aberto."""

    @patch("apps.core.http_client.build_http_client")
    def test_get_converte_circuito_aberto_em_connect_error(
        self,
        mock_build_http_client: MagicMock,
    ) -> None:
        """GET deve converter CircuitOpenError em ConnectError."""
        svc = _make_token_client()

        mock_build_http_client.return_value.get.side_effect = CircuitOpenError(
            "circuito aberto"
        )

        with self.assertRaises(httpx.ConnectError) as contexto:
            svc.get("/api/v1/health/")

        erro = contexto.exception

        self.assertEqual(
            str(erro),
            "Circuit breaker aberto para token",
        )

        self.assertEqual(
            erro.request.method,
            "GET",
        )

        self.assertEqual(
            str(erro.request.url),
            "https://token-ms/api/v1/health/",
        )

    @patch("apps.core.http_client.build_http_client")
    def test_post_converte_circuito_aberto_em_connect_error(
        self,
        mock_build_http_client: MagicMock,
    ) -> None:
        """POST deve converter CircuitOpenError em ConnectError."""
        svc = _make_auditoria_client()

        mock_build_http_client.return_value.post.side_effect = (
            CircuitOpenError("circuito aberto")
        )

        with self.assertRaises(httpx.ConnectError) as contexto:
            svc.post(
                "/api/v1/gatilho-poll/",
                payload={
                    "realm": "COTIC",
                    "usuario_id": "123",
                },
            )

        erro = contexto.exception

        self.assertEqual(
            str(erro),
            "Circuit breaker aberto para auditoria",
        )

        self.assertEqual(
            erro.request.method,
            "POST",
        )

        self.assertEqual(
            str(erro.request.url),
            "https://auditoria-ms/api/v1/gatilho-poll/",
        )

    @patch("apps.core.http_client.build_http_client")
    def test_put_converte_circuito_aberto_em_connect_error(
        self,
        mock_build_http_client: MagicMock,
    ) -> None:
        """PUT deve converter CircuitOpenError em ConnectError."""
        svc = _make_token_client()

        mock_build_http_client.return_value.put.side_effect = CircuitOpenError(
            "circuito aberto"
        )

        with self.assertRaises(httpx.ConnectError) as contexto:
            svc.put(
                "/api/v1/token/123/",
                payload={
                    "perfil": "professor",
                },
            )

        erro = contexto.exception

        self.assertEqual(
            str(erro),
            "Circuit breaker aberto para token",
        )

        self.assertEqual(
            erro.request.method,
            "PUT",
        )

        self.assertEqual(
            str(erro.request.url),
            "https://token-ms/api/v1/token/123/",
        )


class ServiceClientObservabilityTest(SimpleTestCase):
    """Valida a integração de correlação com o SDK."""

    def test_propaga_request_id_pelo_cliente_do_sdk(self) -> None:
        """Deve propagar o correlation id para o Token-MS."""
        seen_headers: dict[str, str] = {}

        def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            seen_headers.update(request.headers)

            return httpx.Response(
                200,
                request=request,
            )

        svc = _make_token_client()

        svc._client = build_http_client(  # noqa: SLF001
            "token",
            base_url="https://token-ms",
            transport=httpx.MockTransport(handler),
        )

        with correlation_context(
            correlation_id="gateway-request-123",
        ):
            svc.get("/api/v1/health/")

        self.assertEqual(
            seen_headers["x-request-id"],
            "gateway-request-123",
        )
