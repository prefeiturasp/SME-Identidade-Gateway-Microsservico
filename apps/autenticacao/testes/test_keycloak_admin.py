"""Testes das funções de gestão de credencial via Keycloak Admin."""

import base64
import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.autenticacao import keycloak_admin


def _access_token_fake(claims: dict) -> str:
    """Monta um JWT sintético (header.payload.signature) para teste.

    A assinatura não é válida — ``decodificar_claims_token`` não a
    verifica, só decodifica o payload.
    """
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=")
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(
        b"="
    )
    return f"{header.decode()}.{payload.decode()}.assinatura-fake"


_CONTA_KC = {
    "id": "5c29cc47-41a1-4ef4-994f-c65aae52d456",
    "username": "1234567",
    "email": "fulano@sme.sp.gov.br",
    "firstName": "FULANO",
    "lastName": "DE TAL",
    "enabled": True,
    "attributes": {"rf": ["1234567"], "cpf": ["12345678900"]},
}


class TestDispararRedefinicaoSenha:
    """Testes de disparar_redefinicao_senha."""

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_deve_disparar_update_password(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Deve chamar send_update_account com UPDATE_PASSWORD."""
        admin = MagicMock()
        admin.get_users.return_value = [_CONTA_KC]
        mock_obter_admin.return_value = admin

        keycloak_admin.disparar_redefinicao_senha("1234567")

        admin.send_update_account.assert_called_once()
        _, kwargs = admin.send_update_account.call_args
        assert kwargs["user_id"] == _CONTA_KC["id"]
        assert kwargs["payload"] == ["UPDATE_PASSWORD"]


class TestDispararVerificacaoEmail:
    """Testes de disparar_verificacao_email."""

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_deve_chamar_send_verify_email(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Deve chamar send_verify_email para o usuário resolvido."""
        admin = MagicMock()
        admin.get_users.return_value = [_CONTA_KC]
        mock_obter_admin.return_value = admin

        keycloak_admin.disparar_verificacao_email("1234567")

        admin.send_verify_email.assert_called_once()
        _, kwargs = admin.send_verify_email.call_args
        assert kwargs["user_id"] == _CONTA_KC["id"]


class TestAlterarEmail:
    """Testes de alterar_email."""

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_deve_atualizar_email_e_reverificar(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Deve atualizar o e-mail e disparar nova verificação."""
        admin = MagicMock()
        admin.get_users.return_value = [_CONTA_KC]
        mock_obter_admin.return_value = admin

        resultado = keycloak_admin.alterar_email(
            "1234567", "novo@sme.sp.gov.br"
        )

        admin.update_user.assert_called_once_with(
            user_id=_CONTA_KC["id"],
            payload={"email": "novo@sme.sp.gov.br"},
        )
        admin.send_verify_email.assert_called_once()
        assert resultado == {
            "email_alterado": True,
            "verificacao_enviada": True,
        }

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_email_alterado_mesmo_se_verificacao_falhar(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Não deve propagar falha de send_verify_email.

        update_user e send_verify_email não são atômicos no
        Keycloak — se a notificação falhar depois da troca já
        aplicada, quem chama precisa saber que o e-mail mudou mesmo
        assim, em vez de receber uma exceção genérica.
        """
        admin = MagicMock()
        admin.get_users.return_value = [_CONTA_KC]
        admin.send_verify_email.side_effect = Exception("instabilidade")
        mock_obter_admin.return_value = admin

        resultado = keycloak_admin.alterar_email(
            "1234567", "novo@sme.sp.gov.br"
        )

        admin.update_user.assert_called_once()
        assert resultado == {
            "email_alterado": True,
            "verificacao_enviada": False,
        }


class TestRedefinirSenha:
    """Testes de redefinir_senha."""

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_deve_definir_senha_como_definitiva(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Deve chamar set_user_password com temporary=False."""
        admin = MagicMock()
        admin.get_users.return_value = [_CONTA_KC]
        mock_obter_admin.return_value = admin

        keycloak_admin.redefinir_senha("1234567", "senha123")

        admin.set_user_password.assert_called_once_with(
            user_id=_CONTA_KC["id"],
            password="senha123",  # NOSONAR
            temporary=False,
        )

    @patch("apps.autenticacao.keycloak_admin.obter_admin_keycloak")
    def test_deve_limpar_required_actions_pendentes(
        self, mock_obter_admin: MagicMock
    ) -> None:
        """Deve remover UPDATE_PASSWORD herdada de senha temporária.

        Sem isso, o password grant continua recusado com
        ``Account is not fully set up`` mesmo após a senha
        definitiva ser aplicada.
        """
        admin = MagicMock()
        admin.get_users.return_value = [_CONTA_KC]
        mock_obter_admin.return_value = admin

        keycloak_admin.redefinir_senha("1234567", "senha123")

        admin.update_user.assert_called_once_with(
            user_id=_CONTA_KC["id"],
            payload={"requiredActions": []},
        )


class TestDecodificarClaimsToken:
    """Testes de decodificar_claims_token."""

    def test_decodifica_claims_de_um_jwt_valido(self) -> None:
        """Deve extrair os claims do payload do token."""
        token = _access_token_fake(
            {"realm_access": {"roles": ["default-roles-cotic"]}}
        )

        claims = keycloak_admin.decodificar_claims_token(token)

        assert claims == {"realm_access": {"roles": ["default-roles-cotic"]}}

    def test_retorna_vazio_para_token_malformado(self) -> None:
        """Deve retornar {} sem lançar exceção para entrada inválida."""
        assert keycloak_admin.decodificar_claims_token("nao-e-um-jwt") == {}
        assert keycloak_admin.decodificar_claims_token("") == {}


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


class TestEncerrarSessao:
    """Testes de encerrar_sessao."""

    def test_encerra_sessao_com_sucesso(self) -> None:
        """Deve confirmar o encerramento e extrair o kc_user_id."""
        refresh_token = _access_token_fake({"sub": _CONTA_KC["id"]})

        mock_kc_openid = MagicMock()
        with patch("keycloak.KeycloakOpenID", return_value=mock_kc_openid):
            resultado = keycloak_admin.encerrar_sessao(refresh_token)

        assert resultado == {
            "encerrada": True,
            "kc_user_id": _CONTA_KC["id"],
        }
        mock_kc_openid.logout.assert_called_once_with(refresh_token)

    def test_token_ja_invalido_nao_e_erro(self) -> None:
        """Deve retornar encerrada=False sem lançar exceção."""
        from keycloak.exceptions import KeycloakPostError

        refresh_token = _access_token_fake({"sub": _CONTA_KC["id"]})

        mock_kc_openid = MagicMock()
        mock_kc_openid.logout.side_effect = KeycloakPostError("token expirado")
        with patch("keycloak.KeycloakOpenID", return_value=mock_kc_openid):
            resultado = keycloak_admin.encerrar_sessao(refresh_token)

        assert resultado == {
            "encerrada": False,
            "kc_user_id": _CONTA_KC["id"],
        }

    def test_refresh_token_malformado_retorna_kc_user_id_none(self) -> None:
        """Deve seguir com o encerramento mesmo sem extrair o sub."""
        mock_kc_openid = MagicMock()
        with patch("keycloak.KeycloakOpenID", return_value=mock_kc_openid):
            resultado = keycloak_admin.encerrar_sessao("nao-e-um-jwt")

        assert resultado["kc_user_id"] is None
        mock_kc_openid.logout.assert_called_once_with("nao-e-um-jwt")


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


@override_settings(
    KEYCLOAK_URL_SERVIDOR="https://keycloak.local",
    KEYCLOAK_USUARIO_ADMIN="admin",
    KEYCLOAK_SENHA_ADMIN="senha",
    KEYCLOAK_REALM="master",
    KEYCLOAK_VERIFICAR_SSL=False,
)
class TestObterAdminKeycloak(SimpleTestCase):
    """Testes de obter_admin_keycloak."""

    @patch("keycloak.KeycloakAdmin")
    def test_deve_instanciar_keycloak_admin(
        self,
        mock_keycloak_admin: MagicMock,
    ) -> None:
        """Deve criar o cliente KeycloakAdmin com as configurações."""
        instancia = MagicMock()
        mock_keycloak_admin.return_value = instancia

        resultado = keycloak_admin.obter_admin_keycloak()

        assert resultado is instancia

        mock_keycloak_admin.assert_called_once_with(
            server_url="https://keycloak.local",
            username="admin",
            password="senha",  # NOSONAR
            realm_name="master",
            user_realm_name="master",
            verify=False,
        )


class TestResolverUserId(SimpleTestCase):
    """Testes de _resolver_user_id."""

    @patch("apps.autenticacao.keycloak_admin.buscar_usuario_por_login")
    def test_deve_retornar_id_do_usuario(
        self,
        mock_buscar: MagicMock,
    ) -> None:
        """Deve retornar o id da conta encontrada."""
        mock_buscar.return_value = {"id": "abc-123"}

        resultado = keycloak_admin._resolver_user_id(
            MagicMock(),
            "1234567",
        )

        assert resultado == "abc-123"

    @patch("apps.autenticacao.keycloak_admin.buscar_usuario_por_login")
    def test_deve_lancar_keycloak_get_error_quando_nao_encontrar(
        self,
        mock_buscar: MagicMock,
    ) -> None:
        """Deve lançar KeycloakGetError quando a conta não existir."""
        from keycloak.exceptions import KeycloakGetError

        mock_buscar.return_value = None

        with self.assertRaises(KeycloakGetError):
            keycloak_admin._resolver_user_id(
                MagicMock(),
                "0000000",
            )


@override_settings(
    KEYCLOAK_URL_SERVIDOR="https://keycloak.local",
    KEYCLOAK_REALM="realm-teste",
    KEYCLOAK_VERIFICAR_SSL=False,
)
class TestAutenticarClient(SimpleTestCase):
    """Testes de autenticar_client."""

    @patch("apps.autenticacao.keycloak_admin.KeycloakOpenID")
    def test_deve_autenticar_client_com_sucesso(
        self,
        mock_keycloak_openid: MagicMock,
    ) -> None:
        """Deve autenticar via Client Credentials e retornar o token."""
        instancia = MagicMock()
        instancia.token.return_value = {
            "access_token": "access-token",
            "expires_in": 300,
            "token_type": "Bearer",
        }
        mock_keycloak_openid.return_value = instancia

        resultado = keycloak_admin.autenticar_client(
            "meu-client",
            "meu-secret",
        )

        assert resultado == {
            "autenticado": True,
            "access_token": "access-token",
            "expires_in": 300,
            "token_type": "Bearer",
        }

        mock_keycloak_openid.assert_called_once_with(
            server_url="https://keycloak.local",
            client_id="meu-client",
            client_secret_key="meu-secret",
            realm_name="realm-teste",
            verify=False,
        )
        instancia.token.assert_called_once_with(
            grant_type="client_credentials",
        )

    @patch("apps.autenticacao.keycloak_admin.KeycloakOpenID")
    def test_deve_usar_bearer_quando_token_type_nao_for_retornado(
        self,
        mock_keycloak_openid: MagicMock,
    ) -> None:
        """Deve assumir Bearer quando token_type não vier do Keycloak."""
        instancia = MagicMock()
        instancia.token.return_value = {
            "access_token": "access-token",
            "expires_in": 300,
        }
        mock_keycloak_openid.return_value = instancia

        resultado = keycloak_admin.autenticar_client(
            "meu-client",
            "meu-secret",
        )

        assert resultado["autenticado"] is True
        assert resultado["token_type"] == "Bearer"

    @patch("apps.autenticacao.keycloak_admin.KeycloakOpenID")
    def test_deve_retornar_access_token_vazio_quando_nao_informado(
        self,
        mock_keycloak_openid: MagicMock,
    ) -> None:
        """Deve retornar string vazia quando access_token não existir."""
        instancia = MagicMock()
        instancia.token.return_value = {
            "expires_in": 300,
            "token_type": "Bearer",
        }
        mock_keycloak_openid.return_value = instancia

        resultado = keycloak_admin.autenticar_client(
            "meu-client",
            "meu-secret",
        )

        assert resultado["autenticado"] is True
        assert resultado["access_token"] == ""

    @patch("apps.autenticacao.keycloak_admin.KeycloakOpenID")
    def test_deve_retornar_erro_para_client_invalido(
        self,
        mock_keycloak_openid: MagicMock,
    ) -> None:
        """Deve retornar erro amigável quando o client for inválido."""
        from keycloak.exceptions import KeycloakAuthenticationError

        instancia = MagicMock()
        instancia.token.side_effect = KeycloakAuthenticationError(
            "invalid_client"
        )
        mock_keycloak_openid.return_value = instancia

        resultado = keycloak_admin.autenticar_client(
            "client-invalido",
            "secret-invalido",
        )

        assert resultado == {
            "autenticado": False,
            "erro": "Client ID ou Client Secret inválidos.",
        }

    @patch("apps.autenticacao.keycloak_admin.KeycloakOpenID")
    def test_deve_retornar_erro_quando_service_account_nao_estiver_habilitada(
        self,
        mock_keycloak_openid: MagicMock,
    ) -> None:
        """Deve informar quando Service Accounts Roles estiver desabilitado."""
        from keycloak.exceptions import KeycloakPostError

        instancia = MagicMock()
        instancia.token.side_effect = KeycloakPostError(
            "Client not enabled to retrieve service account"
        )
        mock_keycloak_openid.return_value = instancia

        resultado = keycloak_admin.autenticar_client(
            "meu-client",
            "meu-secret",
        )

        assert resultado == {
            "autenticado": False,
            "erro": (
                "O client não está habilitado para autenticação via "
                "Client Credentials. Verifique se 'Service Accounts Roles' "
                "está habilitado no Keycloak."
            ),
        }


@override_settings(
    KEYCLOAK_URL_SERVIDOR="https://keycloak.local",
    KEYCLOAK_REALM="realm-teste",
    KEYCLOAK_VERIFICAR_SSL=False,
)
class TestValidarTokenClient(SimpleTestCase):
    """Testes de validar_token_client."""

    @patch("apps.autenticacao.keycloak_admin.KeycloakOpenID")
    def test_deve_validar_token_com_sucesso(
        self,
        mock_keycloak_openid: MagicMock,
    ) -> None:
        """Deve retornar as claims quando o token for válido."""
        instancia = MagicMock()
        instancia.decode_token.return_value = {
            "sub": "service-account-id",
            "preferred_username": "service-account-meu-client",
            "exp": 1234567890,
        }
        mock_keycloak_openid.return_value = instancia

        resultado = keycloak_admin.validar_token_client("access-token")

        assert resultado == {
            "valido": True,
            "expirado": False,
            "claims": {
                "sub": "service-account-id",
                "preferred_username": "service-account-meu-client",
                "exp": 1234567890,
            },
        }

        mock_keycloak_openid.assert_called_once_with(
            server_url="https://keycloak.local",
            realm_name="realm-teste",
            client_id="",
            verify=False,
        )
        instancia.decode_token.assert_called_once_with(
            "access-token",
            validate=True,
        )

    @patch("apps.autenticacao.keycloak_admin.KeycloakOpenID")
    def test_deve_retornar_expirado_para_token_expirado(
        self,
        mock_keycloak_openid: MagicMock,
    ) -> None:
        """Deve distinguir token expirado de outros tokens inválidos."""
        instancia = MagicMock()
        instancia.decode_token.side_effect = keycloak_admin.JWTExpired()
        mock_keycloak_openid.return_value = instancia

        resultado = keycloak_admin.validar_token_client("token-expirado")

        assert resultado == {
            "valido": False,
            "expirado": True,
            "claims": {},
            "detalhe": "Token expirado.",
        }

    @patch("apps.autenticacao.keycloak_admin.KeycloakOpenID")
    def test_deve_retornar_invalido_quando_decode_lancar_value_error(
        self,
        mock_keycloak_openid: MagicMock,
    ) -> None:
        """Deve retornar token inválido para ValueError."""
        instancia = MagicMock()
        instancia.decode_token.side_effect = ValueError("token inválido")
        mock_keycloak_openid.return_value = instancia

        resultado = keycloak_admin.validar_token_client("token-invalido")

        assert resultado == {
            "valido": False,
            "expirado": False,
            "claims": {},
            "detalhe": "Token inválido.",
        }

    @patch("apps.autenticacao.keycloak_admin.KeycloakOpenID")
    def test_deve_retornar_invalido_quando_decode_lancar_key_error(
        self,
        mock_keycloak_openid: MagicMock,
    ) -> None:
        """Deve retornar token inválido para KeyError."""
        instancia = MagicMock()
        instancia.decode_token.side_effect = KeyError("claim")
        mock_keycloak_openid.return_value = instancia

        resultado = keycloak_admin.validar_token_client("token-invalido")

        assert resultado == {
            "valido": False,
            "expirado": False,
            "claims": {},
            "detalhe": "Token inválido.",
        }


class TestObterErroAutenticacaoClient(SimpleTestCase):
    """Testes de _obter_erro_autenticacao_client."""

    def test_deve_retornar_erro_para_service_account_desabilitada(
        self,
    ) -> None:
        """Deve orientar a habilitação de Service Accounts Roles."""
        from keycloak.exceptions import KeycloakPostError

        exc = KeycloakPostError(
            "Client not enabled to retrieve service account"
        )

        resultado = keycloak_admin._obter_erro_autenticacao_client(exc)

        assert resultado == (
            "O client não está habilitado para autenticação via "
            "Client Credentials. Verifique se 'Service Accounts Roles' "
            "está habilitado no Keycloak."
        )

    def test_deve_retornar_erro_para_invalid_client(self) -> None:
        """Deve traduzir invalid_client para mensagem de domínio."""
        from keycloak.exceptions import KeycloakAuthenticationError

        exc = KeycloakAuthenticationError("invalid_client")

        resultado = keycloak_admin._obter_erro_autenticacao_client(exc)

        assert resultado == "Client ID ou Client Secret inválidos."

    def test_deve_retornar_erro_para_unauthorized_client(self) -> None:
        """Deve traduzir unauthorized_client para mensagem de domínio."""
        from keycloak.exceptions import KeycloakPostError

        exc = KeycloakPostError("unauthorized_client")

        resultado = keycloak_admin._obter_erro_autenticacao_client(exc)

        assert resultado == "Client ID ou Client Secret inválidos."

    def test_deve_retornar_erro_generico_para_falha_desconhecida(
        self,
    ) -> None:
        """Deve evitar expor detalhes internos em erros desconhecidos."""
        from keycloak.exceptions import KeycloakPostError

        exc = KeycloakPostError("internal server error")

        resultado = keycloak_admin._obter_erro_autenticacao_client(exc)

        assert resultado == "Não foi possível autenticar o client no Keycloak."
