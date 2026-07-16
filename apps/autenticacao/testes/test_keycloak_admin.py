"""Testes das funções de gestão de credencial via Keycloak Admin."""

import base64
import json
from unittest.mock import MagicMock, patch

from apps.autenticacao import keycloak_admin


def _access_token_fake(claims: dict) -> str:
    """Monta um JWT sintético (header.payload.signature) para teste.

    A assinatura não é válida — ``_decodificar_claims_token`` não a
    verifica, só decodifica o payload.
    """
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=")
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(
        b"="
    )
    return f"{header.decode()}.{payload.decode()}.assinatura-fake"


class TestDispararRedefinicaoSenha:
    """Testes de disparar_redefinicao_senha."""

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_deve_disparar_update_password(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Deve chamar send_update_account com UPDATE_PASSWORD."""
        admin = MagicMock()
        admin.get_user_id.return_value = "uuid-usuario"
        mock_obter_admin.return_value = admin

        keycloak_admin.disparar_redefinicao_senha("1234567")

        admin.get_user_id.assert_called_once_with("1234567")
        admin.send_update_account.assert_called_once()
        _, kwargs = admin.send_update_account.call_args
        assert kwargs["user_id"] == "uuid-usuario"
        assert kwargs["payload"] == ["UPDATE_PASSWORD"]


class TestDispararVerificacaoEmail:
    """Testes de disparar_verificacao_email."""

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_deve_chamar_send_verify_email(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Deve chamar send_verify_email para o usuário resolvido."""
        admin = MagicMock()
        admin.get_user_id.return_value = "uuid-usuario"
        mock_obter_admin.return_value = admin

        keycloak_admin.disparar_verificacao_email("1234567")

        admin.send_verify_email.assert_called_once()
        _, kwargs = admin.send_verify_email.call_args
        assert kwargs["user_id"] == "uuid-usuario"


class TestAlterarEmail:
    """Testes de alterar_email."""

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_deve_atualizar_email_e_reverificar(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Deve atualizar o e-mail e disparar nova verificação."""
        admin = MagicMock()
        admin.get_user_id.return_value = "uuid-usuario"
        mock_obter_admin.return_value = admin

        keycloak_admin.alterar_email("1234567", "novo@sme.sp.gov.br")

        admin.update_user.assert_called_once_with(
            user_id="uuid-usuario",
            payload={"email": "novo@sme.sp.gov.br"},
        )
        admin.send_verify_email.assert_called_once()


class TestRedefinirSenhaTemporaria:
    """Testes de redefinir_senha_temporaria."""

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_deve_definir_senha_como_temporaria(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Deve chamar set_user_password com temporary=True."""
        admin = MagicMock()
        admin.get_user_id.return_value = "uuid-usuario"
        mock_obter_admin.return_value = admin

        keycloak_admin.redefinir_senha_temporaria("1234567", "senha123")

        admin.set_user_password.assert_called_once_with(
            user_id="uuid-usuario",
            password="senha123",  # NOSONAR
            temporary=True,
        )


_CONTA_KC = {
    "id": "5c29cc47-41a1-4ef4-994f-c65aae52d456",
    "username": "1234567",
    "email": "fulano@sme.sp.gov.br",
    "firstName": "FULANO",
    "lastName": "DE TAL",
    "enabled": True,
    "attributes": {"rf": ["1234567"], "cpf": ["12345678900"]},
}


class TestDecodificarClaimsToken:
    """Testes de _decodificar_claims_token."""

    def test_decodifica_claims_de_um_jwt_valido(self) -> None:
        """Deve extrair os claims do payload do token."""
        token = _access_token_fake(
            {"realm_access": {"roles": ["default-roles-cotic"]}}
        )

        claims = keycloak_admin._decodificar_claims_token(token)

        assert claims == {"realm_access": {"roles": ["default-roles-cotic"]}}

    def test_retorna_vazio_para_token_malformado(self) -> None:
        """Deve retornar {} sem lançar exceção para entrada inválida."""
        assert keycloak_admin._decodificar_claims_token("nao-e-um-jwt") == {}
        assert keycloak_admin._decodificar_claims_token("") == {}


class TestBuscarUsuarioPorLogin:
    """Testes de buscar_usuario_por_login."""

    def test_encontra_por_username_exato(self) -> None:
        """Deve encontrar direto na primeira query (username exato)."""
        admin = MagicMock()
        admin.get_users.return_value = [_CONTA_KC]

        resultado = keycloak_admin.buscar_usuario_por_login(admin, "1234567")

        assert resultado == _CONTA_KC
        admin.get_users.assert_called_once_with(
            query={"username": "1234567", "exact": True}
        )

    def test_encontra_por_atributo_rf_quando_username_falha(self) -> None:
        """Deve tentar o atributo rf quando username exato não acha."""
        admin = MagicMock()
        admin.get_users.side_effect = [[], [_CONTA_KC]]

        resultado = keycloak_admin.buscar_usuario_por_login(admin, "1234567")

        assert resultado == _CONTA_KC
        assert admin.get_users.call_count == 2

    def test_inclui_query_de_email_quando_login_tem_arroba(self) -> None:
        """Deve adicionar busca por email quando o login contém @."""
        admin = MagicMock()
        admin.get_users.return_value = []

        keycloak_admin.buscar_usuario_por_login(admin, "fulano@sme.sp.gov.br")

        queries = [c.kwargs["query"] for c in admin.get_users.call_args_list]
        assert {"email": "fulano@sme.sp.gov.br", "exact": True} in queries

    def test_retorna_none_quando_nao_encontra(self) -> None:
        """Deve retornar None se nenhuma query encontrar a conta."""
        admin = MagicMock()
        admin.get_users.return_value = []

        resultado = keycloak_admin.buscar_usuario_por_login(admin, "0000000")

        assert resultado is None


class TestAutenticar:
    """Testes de autenticar."""

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_usuario_nao_encontrado_retorna_erro(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Deve retornar autenticado=False sem tentar login no KC."""
        admin = MagicMock()
        admin.get_users.return_value = []
        mock_obter_admin.return_value = admin

        resultado = keycloak_admin.autenticar("0000000", "senha")

        assert resultado == {
            "autenticado": False,
            "erro": "usuário não encontrado",
        }

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_autentica_com_sucesso(self, mock_obter_admin: MagicMock) -> None:
        """Deve autenticar e retornar dados da conta, roles e tokens."""
        admin = MagicMock()
        admin.get_users.return_value = [_CONTA_KC]
        mock_obter_admin.return_value = admin

        mock_kc_openid = MagicMock()
        mock_kc_openid.token.return_value = {
            "access_token": _access_token_fake(
                {
                    "realm_access": {"roles": ["default-roles-cotic"]},
                    "resource_access": {
                        "auto-servico-qa": {"roles": ["COTIC"]}
                    },
                }
            ),
            "refresh_token": "refresh-jwt",
            "expires_in": 300,
        }
        with patch("keycloak.KeycloakOpenID", return_value=mock_kc_openid):
            resultado = keycloak_admin.autenticar("1234567", "senha123")

        assert resultado["autenticado"] is True
        assert resultado["kc_user_id"] == _CONTA_KC["id"]
        assert resultado["username"] == "1234567"
        assert resultado["nome"] == "FULANO DE TAL"
        assert resultado["roles"]["realm_access"] == {
            "roles": ["default-roles-cotic"]
        }
        assert resultado["roles"]["resource_access"] == {
            "auto-servico-qa": {"roles": ["COTIC"]}
        }
        mock_kc_openid.token.assert_called_once_with("1234567", "senha123")

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_token_sem_claims_de_roles_retorna_roles_vazias(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Deve retornar roles vazias se o token não trouxer os claims."""
        admin = MagicMock()
        admin.get_users.return_value = [_CONTA_KC]
        mock_obter_admin.return_value = admin

        mock_kc_openid = MagicMock()
        mock_kc_openid.token.return_value = {
            "access_token": _access_token_fake({}),
            "refresh_token": "refresh-jwt",
            "expires_in": 300,
        }
        with patch("keycloak.KeycloakOpenID", return_value=mock_kc_openid):
            resultado = keycloak_admin.autenticar("1234567", "senha123")

        assert resultado["roles"] == {
            "realm_access": {},
            "resource_access": {},
        }

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_senha_invalida_retorna_erro(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Deve retornar autenticado=False quando o token() falhar."""
        admin = MagicMock()
        admin.get_users.return_value = [_CONTA_KC]
        mock_obter_admin.return_value = admin

        mock_kc_openid = MagicMock()
        mock_kc_openid.token.side_effect = Exception("invalid_grant")
        with patch("keycloak.KeycloakOpenID", return_value=mock_kc_openid):
            resultado = keycloak_admin.autenticar("1234567", "senha-errada")

        assert resultado["autenticado"] is False
        assert "invalid_grant" in resultado["erro"]


class TestObterDadosUsuario:
    """Testes de obter_dados_usuario."""

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_retorna_dados_quando_encontrado(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Deve retornar os dados normalizados da conta."""
        admin = MagicMock()
        admin.get_users.return_value = [_CONTA_KC]
        mock_obter_admin.return_value = admin

        resultado = keycloak_admin.obter_dados_usuario("1234567")

        assert resultado is not None
        assert resultado["kc_user_id"] == _CONTA_KC["id"]
        assert resultado["nome"] == "FULANO DE TAL"
        assert resultado["cpf"] == "12345678900"
        assert resultado["rf"] == "1234567"
        assert "roles" not in resultado

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_retorna_none_quando_nao_encontrado(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Deve retornar None quando a conta não existir."""
        admin = MagicMock()
        admin.get_users.return_value = []
        mock_obter_admin.return_value = admin

        resultado = keycloak_admin.obter_dados_usuario("0000000")

        assert resultado is None
