"""Testes dos serviços EOL autenticação SGP."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import httpx
import pytest

from apps.eol_autenticacao_sgp import services

_DADOS_ETL = {
    "nome": "USUARIO TESTE",
    "cpf": "00123456789",
    "email": "usuario@exemplo.com",
    "codigo_rf": "1234567",
}


def _resposta(
    codigo: int,
    dados: object | None = None,
    *,
    conteudo: bytes | None = None,
) -> httpx.Response:
    """Cria uma resposta HTTP simulada.

    Args:
        codigo: Código de resposta HTTP.
        dados: Conteúdo JSON da resposta.
        conteudo: Conteúdo bruto para respostas sem JSON válido.

    Returns:
        Resposta HTTP simulada.
    """
    requisicao = httpx.Request(
        "GET",
        "https://servico-teste/api/consulta",
    )

    if conteudo is not None:
        return httpx.Response(
            codigo,
            content=conteudo,
            request=requisicao,
        )

    if dados is not None:
        return httpx.Response(
            codigo,
            json=dados,
            request=requisicao,
        )

    return httpx.Response(codigo, request=requisicao)


@pytest.fixture
def clientes_http() -> Generator[tuple[MagicMock, MagicMock], None, None]:
    """Fornece os clientes HTTP do ETL e da Abrangência simulados."""
    etl = MagicMock()
    abrangencia = MagicMock()

    clientes = {
        "etl": etl,
        "abrangencia": abrangencia,
    }

    with patch(
        "apps.eol_autenticacao_sgp.services.get_api_client",
        side_effect=clientes.__getitem__,
    ):
        yield etl, abrangencia


class TestServicoDadosUsuario:
    """Testa a composição dos dados e a ordem das consultas."""

    def test_encontra_usuario_no_etl_sem_consultar_abrangencia(
        self,
        clientes_http: tuple[MagicMock, MagicMock],
    ) -> None:
        """Retorna os dados cadastrais quando o ETL encontra o usuário."""
        etl, abrangencia = clientes_http
        etl.get.return_value = _resposta(200, _DADOS_ETL)

        dados = services.ServicoDadosUsuario().carregar("1234567")

        assert dados == {
            "cpf": "00123456789",
            "nome": "USUARIO TESTE",
            "codigoRf": "1234567",
            "email": "usuario@exemplo.com",
            "dreCodigo": None,
            "emailValido": True,
        }

        etl.get.assert_called_once_with(
            "/api/v1/etl/coresso/usuarios/1234567/dados/"
        )
        abrangencia.get.assert_not_called()

    @pytest.mark.parametrize(
        ("email", "valido"),
        [
            (None, False),
            ("", False),
            ("sem-arroba", False),
            ("usuario@exemplo.com", True),
        ],
    )
    def test_valida_email_recebido_do_etl(
        self,
        clientes_http: tuple[MagicMock, MagicMock],
        email: str | None,
        valido: bool,
    ) -> None:
        """Anula e-mails inválidos e mantém e-mails válidos."""
        etl, abrangencia = clientes_http

        etl.get.return_value = _resposta(
            200,
            {**_DADOS_ETL, "email": email},
        )

        dados = services.ServicoDadosUsuario().carregar("1234567")

        assert dados is not None
        assert dados["email"] == (email if valido else None)
        assert dados["emailValido"] is valido
        abrangencia.get.assert_not_called()

    @pytest.mark.parametrize(
        ("login", "codigo_rf"),
        [
            ("0001234567", "0001234567"),
            ("1234567", "1234567"),
            ("2147483647", "2147483647"),
            ("2147483648", None),
            ("-2147483648", "-2147483648"),
            ("-2147483649", None),
            ("usuario.teste", None),
        ],
    )
    def test_preenche_codigo_rf_a_partir_do_login(
        self,
        clientes_http: tuple[MagicMock, MagicMock],
        login: str,
        codigo_rf: str | None,
    ) -> None:
        """Preserva o login somente quando convertido para Int32."""
        etl, _ = clientes_http
        etl.get.return_value = _resposta(200, _DADOS_ETL)

        dados = services.ServicoDadosUsuario().carregar(login)

        assert dados is not None
        assert dados["codigoRf"] == codigo_rf

    def test_sem_usuario_consulta_dre_vigente(
        self,
        clientes_http: tuple[MagicMock, MagicMock],
    ) -> None:
        """Consulta a DRE somente quando o ETL não encontra o usuário."""
        etl, abrangencia = clientes_http

        etl.get.return_value = _resposta(204)
        abrangencia.get.return_value = _resposta(
            200,
            {
                "login": "1234567",
                "dreCodigo": "108600",
            },
        )

        dados = services.ServicoDadosUsuario().carregar("1234567")

        assert dados == {
            "cpf": None,
            "nome": None,
            "codigoRf": None,
            "email": None,
            "dreCodigo": "108600",
            "emailValido": False,
        }

        abrangencia.get.assert_called_once_with(
            "/api/abrangencia/usuarios/1234567/dre-vigente"
        )

    def test_sem_usuario_e_sem_dre_retorna_none(
        self,
        clientes_http: tuple[MagicMock, MagicMock],
    ) -> None:
        """Retorna None quando nenhuma das fontes encontra informações."""
        etl, abrangencia = clientes_http

        etl.get.return_value = _resposta(204)
        abrangencia.get.return_value = _resposta(204)

        resultado = services.ServicoDadosUsuario().carregar("1234567")

        assert resultado is None
        abrangencia.get.assert_called_once()

    def test_falha_sql_informada_pelo_etl(
        self,
        clientes_http: tuple[MagicMock, MagicMock],
    ) -> None:
        """Distingue erro SQL de ausência de usuário."""
        etl, abrangencia = clientes_http

        etl.get.return_value = _resposta(
            503,
            {"codigo": "ERRO_CONSULTA_CORESSO"},
        )

        servico = services.ServicoDadosUsuario()

        with pytest.raises(services.ConsultaCoreSSOError):
            servico.carregar("1234567")

        abrangencia.get.assert_not_called()

    @pytest.mark.parametrize("codigo", [401, 404, 500])
    def test_status_inesperado_do_etl(
        self,
        clientes_http: tuple[MagicMock, MagicMock],
        codigo: int,
    ) -> None:
        """Propaga falhas HTTP do ETL sem consultar a Abrangência."""
        etl, abrangencia = clientes_http
        etl.get.return_value = _resposta(codigo)

        servico = services.ServicoDadosUsuario()

        with pytest.raises(services.IntegracaoETLError):
            servico.carregar("1234567")

        abrangencia.get.assert_not_called()

    def test_falha_http_da_abrangencia(
        self,
        clientes_http: tuple[MagicMock, MagicMock],
    ) -> None:
        """Não interpreta erro HTTP da Abrangência como ausência de DRE."""
        etl, abrangencia = clientes_http
        etl.get.return_value = _resposta(204)
        abrangencia.get.return_value = _resposta(503)

        servico = services.ServicoDadosUsuario()

        with pytest.raises(services.ConsultaAbrangenciaError):
            servico.carregar("1234567")

    def test_falha_de_transporte_e_propagada(
        self,
        clientes_http: tuple[MagicMock, MagicMock],
    ) -> None:
        """Propaga a falha de transporte do cliente HTTP."""
        etl, abrangencia = clientes_http

        requisicao = httpx.Request(
            "GET",
            "https://etl-teste/api/consulta",
        )
        etl.get.side_effect = httpx.ConnectError(
            "conexão indisponível",
            request=requisicao,
        )

        servico = services.ServicoDadosUsuario()

        with pytest.raises(httpx.ConnectError):
            servico.carregar("1234567")

        abrangencia.get.assert_not_called()

    def test_etl_503_com_json_invalido(
        self,
        clientes_http: tuple[MagicMock, MagicMock],
    ) -> None:
        """Trata HTTP 503 com JSON inválido como falha do ETL."""
        etl, abrangencia = clientes_http

        etl.get.return_value = _resposta(
            503,
            conteudo=b"json invalido",
        )

        servico = services.ServicoDadosUsuario()

        with pytest.raises(
            services.IntegracaoETLError,
            match="MS-ETL retornou HTTP 503",
        ):
            servico.carregar("1234567")

        abrangencia.get.assert_not_called()

    def test_etl_200_com_json_invalido(
        self,
        clientes_http: tuple[MagicMock, MagicMock],
    ) -> None:
        """Trata JSON inválido do ETL como erro de integração."""
        etl, abrangencia = clientes_http

        etl.get.return_value = _resposta(
            200,
            conteudo=b"json invalido",
        )

        servico = services.ServicoDadosUsuario()

        with pytest.raises(
            services.IntegracaoETLError,
            match="Resposta JSON inválida do MS-ETL",
        ):
            servico.carregar("1234567")

        abrangencia.get.assert_not_called()

    def test_abrangencia_200_com_json_invalido(
        self,
        clientes_http: tuple[MagicMock, MagicMock],
    ) -> None:
        """Trata JSON inválido da Abrangência como erro de consulta."""
        etl, abrangencia = clientes_http

        etl.get.return_value = _resposta(204)
        abrangencia.get.return_value = _resposta(
            200,
            conteudo=b"json invalido",
        )

        servico = services.ServicoDadosUsuario()

        with pytest.raises(
            services.ConsultaAbrangenciaError,
            match="Resposta JSON inválida do MS-Abrangência",
        ):
            servico.carregar("1234567")

        etl.get.assert_called_once()
        abrangencia.get.assert_called_once()

    def test_login_int32_com_erro_de_conversao(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Retorna False quando a conversão para Int32 falha."""
        conversor = MagicMock(side_effect=ValueError("Valor inválido"))

        monkeypatch.setattr(
            services,
            "int",
            conversor,
            raising=False,
        )

        resultado = services._login_eh_int32("1234567")

        assert resultado is False
        conversor.assert_called_once_with("1234567")

    @pytest.mark.parametrize(
        "dados",
        [
            [],
            "resposta invalida",
            123,
        ],
    )
    def test_etl_200_com_json_que_nao_e_objeto(
        self,
        clientes_http: tuple[MagicMock, MagicMock],
        dados: object,
    ) -> None:
        """Rejeita respostas JSON do ETL que não sejam objetos."""
        etl, abrangencia = clientes_http

        etl.get.return_value = _resposta(200, dados)

        servico = services.ServicoDadosUsuario()

        with pytest.raises(
            services.IntegracaoETLError,
            match="Resposta do MS-ETL deve ser um objeto JSON",
        ):
            servico.carregar("1234567")

        etl.get.assert_called_once()
        abrangencia.get.assert_not_called()

    @pytest.mark.parametrize(
        "dados",
        [
            {},
            {"dreCodigo": None},
        ],
    )
    def test_abrangencia_200_sem_dre_codigo_retorna_none(
        self,
        clientes_http: tuple[MagicMock, MagicMock],
        dados: dict[str, object],
    ) -> None:
        """Retorna None quando a Abrangência não informa uma DRE."""
        etl, abrangencia = clientes_http

        etl.get.return_value = _resposta(204)
        abrangencia.get.return_value = _resposta(200, dados)

        resultado = services.ServicoDadosUsuario().carregar("1234567")

        assert resultado is None

        etl.get.assert_called_once()
        abrangencia.get.assert_called_once_with(
            "/api/abrangencia/usuarios/1234567/dre-vigente"
        )
