# Autenticação e Níveis de Acesso

Definido em `apps/autenticacao/`. Todas as rotas exigem `AutenticacaoApiKey`
(header configurável, comparado a `settings.API_KEY` — mesmo padrão usado no
SME-Identidade-ETL).

Rotas registradas sob `identidade-gateway/api/v1/autenticacao/`.

---

## Login e dados do usuário (real — Keycloak)

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/login/` | Autentica um usuário via OpenID Connect |
| `GET` | `/usuarios/{login}/dados/` | Dados cadastrais do usuário |

`login` aceita RF, CPF, e-mail ou o username do Keycloak — a resolução usa
a mesma estratégia do comando `validar_login` do SME-Identidade-ETL: tenta
username exato, depois os atributos customizados `rf` e `cpf`, e por
último e-mail (se o valor contiver `@`).

`POST /login/` resolve a conta e autentica a senha via
`KeycloakOpenID.token()` (grant type `password`) — não é mock, é login
real contra o Keycloak.

```json
// POST /login/
{
  "login": "1234567",
  "senha": "..."
}
```

```json
// 200
{
  "kc_user_id": "5c29cc47-...",
  "username": "1234567",
  "nome": "FULANO DE TAL",
  "email": "fulano@sme.prefeitura.sp.gov.br",
  "ativo": true,
  "cpf": "12345678900",
  "rf": "1234567",
  "roles": {
    "realm_access": {"roles": ["default-roles-cotic"]},
    "resource_access": {
      "auto-servico-qa": {"roles": ["COTIC"]}
    }
  },
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "expires_in": 300
}
```

`roles` vem no formato bruto do Keycloak (`realm_access`/`resource_access`),
extraído direto dos claims do access token — sem filtragem ou renomeação.
Depende dos protocol mappers configurados no client de login
(`KEYCLOAK_LOGIN_CLIENT_ID`); `admin-cli` não os inclui, `auto-servico-qa`
sim.

`GET /usuarios/{login}/dados/` retorna o mesmo formato, **sem** `roles` e
sem os tokens (mesma resolução de `login`, sem autenticar senha). Montar
`roles` aqui exigiria iterar todos os clients do realm via Admin API (~9
chamadas por requisição, pois este fluxo não emite um token do próprio
usuário) — testado e descartado por lentidão. Token Exchange (RFC 8693) foi
avaliado como alternativa de 1 chamada, mas não está habilitado nesta
instância do Keycloak (`Standard token exchange is not enabled for the
requested client`).

**Erros:**

| Situação | Status |
|---|---|
| Login não encontrado no Keycloak | `204 No Content` (sem corpo) |
| Senha incorreta | `401` |
| Usuário não encontrado (`GET /usuarios/{login}/dados/`) | `204 No Content` (sem corpo) |

`204` não tem corpo por definição do protocolo HTTP — o cliente distingue
"não encontrado" (204) de "encontrado" (200 com corpo) só pelo status, sem
mensagem de detalhe.

### Funções em `keycloak_admin.py` (login)

| Função | Ação no Keycloak |
|---|---|
| `buscar_usuario_por_login(admin, login)` | `get_users()` por username exato, depois atributos `rf`/`cpf`/`email` |
| `autenticar(login, senha)` | Resolve a conta e chama `KeycloakOpenID.token()` (grant `password`) |
| `obter_dados_usuario(login)` | Resolve a conta e retorna os dados normalizados |

---

## Níveis de acesso (mockado)

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/usuarios/{login}/perfis/` | Perfis de acesso do usuário |
| `GET` | `/usuarios/{login}/perfis/{perfil}/acesso/` | Token enriquecido + permissões do perfil |

**Estado atual:** as respostas são mockadas — o SME-Identidade-Token-Microsservico,
que fornecerá os dados reais de perfil e abrangência, ainda está em
desenvolvimento por outro time. O contrato (paths, payloads) já reflete o
formato final esperado, para que a troca do mock pela chamada real ao
token-ms não exija mudança de assinatura.

---

## Gestão de credencial (real — Keycloak)

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/alterar-senha/` | Define senha definitiva (não exige troca no próximo login) |
| `POST` | `/alterar-email/` | Atualiza e-mail e reabre a verificação |

> `POST /recuperar-senha/` está **desativada temporariamente** (rota removida
> de `apps/autenticacao/api/urls.py` e do Swagger) — `send_update_account`
> está instável no Keycloak de QA, retornando `502` de forma recorrente. A
> view e a lógica em `keycloak_admin.disparar_redefinicao_senha` continuam no
> código; basta devolver a rota para reativar.

Diferente das rotas de login, estas **já operam contra o Keycloak de
verdade** via `apps/autenticacao/keycloak_admin.py` (`KeycloakAdmin`, lib
`python-keycloak` — mesmo padrão de conexão do ETL). Gestão de credencial é
responsabilidade nativa do Keycloak: nenhum token de recuperação de senha é
gerado, armazenado ou validado por este serviço — todo o mecanismo (link
assinado, expiração, envio de e-mail) é do próprio Keycloak.

```json
// POST /recuperar-senha/
{"login": "1234567"}
```

```json
// POST /alterar-senha/
{"login": "1234567", "senha": "novaSenha"}
```

```json
// POST /alterar-email/
{"login": "1234567", "email": "novo@sme.prefeitura.sp.gov.br"}
```

**Retorno de sucesso (`recuperar-senha/` e `alterar-senha/`):**

```json
{"situacao": "solicitacao_enviada"}
```

**Retorno de sucesso (`alterar-email/`):**

```json
{"situacao": "email_alterado", "verificacao_enviada": true}
```

`update_user` (troca do e-mail) e `send_verify_email` (envio da notificação) não
são atômicos no Keycloak. Se a troca for aplicada mas o envio da verificação
falhar (ex.: instabilidade do servidor), a resposta continua `200` — o e-mail
já mudou de fato — com `verificacao_enviada: false` no corpo, em vez de um
erro genérico que sugeriria que nada foi aplicado. Repita a chamada com o
mesmo e-mail para reenviar a verificação.

Se o `login` não existir no Keycloak, todas as rotas retornam `204 No
Content` (sem corpo).

### Funções em `keycloak_admin.py`

| Função | Ação no Keycloak |
|---|---|
| `disparar_redefinicao_senha(login)` | `send_update_account(payload=["UPDATE_PASSWORD"])` |
| `redefinir_senha(login, senha)` | `set_user_password(temporary=False)` |
| `alterar_email(login, novo_email)` | `update_user(payload={"email": ...})` + `send_verify_email` |
| `disparar_verificacao_email(login)` | `send_verify_email` |

---

## Configuração

| Variável | Padrão | Descrição |
|---|---|---|
| `API_KEY` | — | Chave exigida dos clientes que chamam o Gateway |
| `API_KEY_HEADER` | `X-API-Key` | Header onde a chave é enviada |
| `KEYCLOAK_URL_SERVIDOR` | `https://localhost:8080/` | URL do Keycloak |
| `KEYCLOAK_REALM` | `COTIC` | Realm de destino |
| `KEYCLOAK_USUARIO_ADMIN` / `KEYCLOAK_SENHA_ADMIN` | `admin` / `admin` | Credenciais do `KeycloakAdmin` |
| `KEYCLOAK_VERIFICAR_SSL` | `true` | Verificação de certificado TLS |
| `KEYCLOAK_LOGIN_CLIENT_ID` | `auto-servico-qa` | Client OIDC usado no login (grant `password`) — precisa ter Direct Access Grants habilitado e os protocol mappers de `realm_access`/`resource_access` configurados |
| `KEYCLOAK_LOGIN_CLIENT_SECRET` | vazio | Secret do client de login (obrigatório — `auto-servico-qa` é confidencial) |

`KEYCLOAK_LOGIN_CLIENT_ID` é distinto de `KEYCLOAK_CLIENT_ID`: o primeiro
autentica usuário final (login), o segundo é usado só pela Admin API para
required actions. `auto-servico-qa` é confidencial (exige `client_secret`)
e é o client com os protocol mappers de roles configurados no realm
`COTIC`; `admin-cli` é público mas não inclui `realm_access`/
`resource_access` no token. Direct Access Grants foi habilitado
manualmente no `auto-servico-qa` via Admin API (não vem habilitado por
padrão em clients confidenciais).
