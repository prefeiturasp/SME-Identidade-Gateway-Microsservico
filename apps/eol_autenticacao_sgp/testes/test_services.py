"""Testes dos serviços EOL autenticação SGP."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import httpx
import pytest

from apps.eol_autenticacao_sgp import services

_USUARIO_ATIVO = {
    "kc_user_id": "b68ac72d-4bca-49de-bba1-a1ae9750905a",
    "username": "1234567",
    "nome": "USUARIO TESTE",
    "cpf": "00123456789",
    "rf": "1234567",
    "email": "usuario@exemplo.com",
    "ativo": True,
}

_DADOS_USUARIO = {
    "cpf": "00123456789",
    "nome": "USUARIO TESTE",
    "codigoRf": "1234567",
    "email": "usuario@exemplo.com",
    "dreCodigo": None,
    "emailValido": True,
}

_DADOS_DRE = {
    "cpf": None,
    "nome": None,
    "codigoRf": None,
    "email": None,
    "dreCodigo": "108600",
    "emailValido": False,
}


def _resposta(
    codigo: int,
    dados: object | None = None,
    *,
    conteudo: bytes | None = None,
) -> httpx.Response:
    """Cria uma resposta HTTP para o MS-Abrangência."""
    requisicao = httpx.Request(
        "GET",
        "https://abrangencia-teste/api/consulta",
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
def integracoes() -> (
    Generator[tuple[MagicMock, MagicMock, MagicMock], None, None]
):
    """Simula a consulta ao Keycloak e o cliente da Abrangência."""
    with (
        patch(
            "apps.eol_autenticacao_sgp.services."
            "keycloak_admin.obter_dados_usuario"
        ) as buscar_usuario,
        patch(
            "apps.eol_autenticacao_sgp.services.get_api_client"
        ) as obter_cliente,
    ):
        cliente_abrangencia = MagicMock()
        obter_cliente.return_value = cliente_abrangencia
        yield buscar_usuario, obter_cliente, cliente_abrangencia


class TestServicoDadosUsuario:
    """Testa a composição do DTO e o fallback para a DRE vigente."""

    def test_usuario_ativo_retorna_dados_sem_consultar_abrangencia(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
    ) -> None:
        """Retorna dados do Keycloak sem buscar DRE."""
        buscar_usuario, obter_cliente, cliente_abrangencia = integracoes
        buscar_usuario.return_value = _USUARIO_ATIVO.copy()

        dados = services.ServicoDadosUsuario().carregar("1234567")

        assert dados == _DADOS_USUARIO
        buscar_usuario.assert_called_once_with("1234567")
        obter_cliente.assert_not_called()
        cliente_abrangencia.get.assert_not_called()

    @pytest.mark.parametrize(
        ("email", "esperado", "valido"),
        [
            ("usuario@exemplo.com", "usuario@exemplo.com", True),
            ("sem-arroba", None, False),
            ("", None, False),
            (None, None, False),
        ],
    )
    def test_valida_email_do_usuario_ativo(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
        email: str | None,
        esperado: str | None,
        valido: bool,
    ) -> None:
        """Preserva somente e-mails válidos no DTO."""
        buscar_usuario, obter_cliente, _ = integracoes
        buscar_usuario.return_value = {
            **_USUARIO_ATIVO,
            "email": email,
        }

        dados = services.ServicoDadosUsuario().carregar("1234567")

        assert dados is not None
        assert dados["email"] == esperado
        assert dados["emailValido"] is valido
        obter_cliente.assert_not_called()

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
    def test_codigo_rf_depende_do_login_int32(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
        login: str,
        codigo_rf: str | None,
    ) -> None:
        """Utiliza o login original quando ele representa um Int32."""
        buscar_usuario, obter_cliente, _ = integracoes
        buscar_usuario.return_value = _USUARIO_ATIVO.copy()

        dados = services.ServicoDadosUsuario().carregar(login)

        assert dados is not None
        assert dados["codigoRf"] == codigo_rf
        buscar_usuario.assert_called_once_with(login)
        obter_cliente.assert_not_called()

    def test_usuario_ativo_com_campos_nulos_nao_consulta_dre(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
    ) -> None:
        """Não confunde atributos vazios com usuário inexistente."""
        buscar_usuario, obter_cliente, _ = integracoes
        buscar_usuario.return_value = {
            **_USUARIO_ATIVO,
            "cpf": None,
            "nome": None,
            "email": None,
        }

        dados = services.ServicoDadosUsuario().carregar("1234567")

        assert dados == {
            "cpf": None,
            "nome": None,
            "codigoRf": "1234567",
            "email": None,
            "dreCodigo": None,
            "emailValido": False,
        }
        obter_cliente.assert_not_called()

    @pytest.mark.parametrize(
        "usuario",
        [
            None,
            {**_USUARIO_ATIVO, "ativo": False},
        ],
    )
    def test_usuario_ausente_ou_inativo_consulta_dre(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
        usuario: dict | None,
    ) -> None:
        """Busca a DRE para usuários ausentes ou inativos."""
        buscar_usuario, obter_cliente, cliente_abrangencia = integracoes
        buscar_usuario.return_value = usuario
        cliente_abrangencia.get.return_value = _resposta(
            200,
            {"login": "1234567", "dreCodigo": "108600"},
        )

        dados = services.ServicoDadosUsuario().carregar("1234567")

        assert dados == _DADOS_DRE
        buscar_usuario.assert_called_once_with("1234567")
        obter_cliente.assert_called_once_with("abrangencia")
        cliente_abrangencia.get.assert_called_once_with(
            "/api/abrangencia/usuarios/1234567/dre-vigente"
        )

    @pytest.mark.parametrize(
        "usuario",
        [
            None,
            {**_USUARIO_ATIVO, "ativo": False},
        ],
    )
    def test_usuario_sem_dre_retorna_none(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
        usuario: dict | None,
    ) -> None:
        """Retorna None quando não há usuário elegível nem DRE."""
        buscar_usuario, obter_cliente, cliente_abrangencia = integracoes
        buscar_usuario.return_value = usuario
        cliente_abrangencia.get.return_value = _resposta(204)

        dados = services.ServicoDadosUsuario().carregar("1234567")

        assert dados is None
        obter_cliente.assert_called_once_with("abrangencia")
        cliente_abrangencia.get.assert_called_once_with(
            "/api/abrangencia/usuarios/1234567/dre-vigente"
        )

    def test_codigo_dre_numerico_e_convertido_para_texto(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
    ) -> None:
        """Normaliza a DRE numérica recebida da Abrangência."""
        buscar_usuario, _, cliente_abrangencia = integracoes
        buscar_usuario.return_value = None
        cliente_abrangencia.get.return_value = _resposta(
            200,
            {"login": "1234567", "dreCodigo": 108600},
        )

        dados = services.ServicoDadosUsuario().carregar("1234567")

        assert dados is not None
        assert dados["dreCodigo"] == "108600"

    def test_erro_no_keycloak_nao_consulta_abrangencia(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
    ) -> None:
        """Propaga falha do Keycloak sem acionar o fallback."""
        buscar_usuario, obter_cliente, _ = integracoes
        buscar_usuario.side_effect = RuntimeError("Keycloak indisponível")
        servico = services.ServicoDadosUsuario()

        with pytest.raises(RuntimeError, match="Keycloak indisponível"):
            servico.carregar("1234567")

        obter_cliente.assert_not_called()

    @pytest.mark.parametrize("codigo", [400, 401, 404, 500, 503])
    def test_erro_http_da_abrangencia(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
        codigo: int,
    ) -> None:
        """Rejeita códigos HTTP diferentes de 200 e 204."""
        buscar_usuario, _, cliente_abrangencia = integracoes
        buscar_usuario.return_value = None
        cliente_abrangencia.get.return_value = _resposta(codigo)
        servico = services.ServicoDadosUsuario()

        with pytest.raises(services.ConsultaAbrangenciaError):
            servico.carregar("1234567")

    def test_json_invalido_da_abrangencia(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
    ) -> None:
        """Rejeita resposta que não contém JSON válido."""
        buscar_usuario, _, cliente_abrangencia = integracoes
        buscar_usuario.return_value = None
        cliente_abrangencia.get.return_value = _resposta(
            200,
            conteudo=b"{invalido",
        )
        servico = services.ServicoDadosUsuario()

        with pytest.raises(services.ConsultaAbrangenciaError):
            servico.carregar("1234567")

    @pytest.mark.parametrize("dados", [[], None, "texto"])
    def test_contrato_invalido_da_abrangencia(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
        dados: object,
    ) -> None:
        """Rejeita respostas fora do contrato da DRE vigente."""
        buscar_usuario, _, cliente_abrangencia = integracoes
        buscar_usuario.return_value = None
        cliente_abrangencia.get.return_value = _resposta(
            200,
            dados if dados is not None else "null",
            conteudo=b"null" if dados is None else None,
        )
        servico = services.ServicoDadosUsuario()

        with pytest.raises(services.ConsultaAbrangenciaError):
            servico.carregar("1234567")

    def test_login_divergente_da_abrangencia(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
    ) -> None:
        """Rejeita resposta referente a outro login."""
        buscar_usuario, _, cliente_abrangencia = integracoes
        buscar_usuario.return_value = None
        cliente_abrangencia.get.return_value = _resposta(
            200,
            {"login": "outro-login", "dreCodigo": "108600"},
        )
        servico = services.ServicoDadosUsuario()

        with pytest.raises(services.ConsultaAbrangenciaError):
            servico.carregar("1234567")

    @pytest.mark.parametrize(
        "codigo",
        [None, "", "  ", True, [], {}],
    )
    def test_codigo_dre_invalido(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
        codigo: object,
    ) -> None:
        """Rejeita códigos de DRE ausentes ou fora do contrato."""
        buscar_usuario, _, cliente_abrangencia = integracoes
        buscar_usuario.return_value = None
        cliente_abrangencia.get.return_value = _resposta(
            200,
            {"login": "1234567", "dreCodigo": codigo},
        )
        servico = services.ServicoDadosUsuario()

        with pytest.raises(services.ConsultaAbrangenciaError):
            servico.carregar("1234567")

    def test_falha_de_conexao_com_abrangencia(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
    ) -> None:
        """Propaga falha de transporte do cliente HTTP."""
        buscar_usuario, _, cliente_abrangencia = integracoes
        buscar_usuario.return_value = None
        requisicao = httpx.Request(
            "GET",
            "https://abrangencia-teste/api/consulta",
        )
        cliente_abrangencia.get.side_effect = httpx.ConnectError(
            "Conexão recusada",
            request=requisicao,
        )
        servico = services.ServicoDadosUsuario()

        with pytest.raises(httpx.ConnectError):
            servico.carregar("1234567")

    def test_falha_na_conversao_do_login_retorna_codigo_rf_nulo(
        self,
        integracoes: tuple[MagicMock, MagicMock, MagicMock],
    ) -> None:
        """Retorna RF nulo quando a conversão numérica falha."""
        buscar_usuario, obter_cliente, _ = integracoes
        buscar_usuario.return_value = _USUARIO_ATIVO.copy()

        servico = services.ServicoDadosUsuario()

        with patch.object(
            services,
            "int",
            side_effect=ValueError("Conversão inválida"),
            create=True,
        ):
            dados = servico.carregar("1234567")

        assert dados is not None
        assert dados["codigoRf"] is None
        buscar_usuario.assert_called_once_with("1234567")
        obter_cliente.assert_not_called()
