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
real contra o Keycloak. Numa única resposta, também solicita ao
SME-Identidade-Token-Microsservico a geração do **token enriquecido**,
não sendo necessária uma segunda chamada para obtê-lo. `perfis` e
`permissoes` fazem parte das claims do
`token_enriquecido`; para obtê-los sem decodificar o JWT, usar
`GET /usuarios/{login}/perfis/` ou
`GET /usuarios/{login}/perfis/{perfil}/acesso/`, que retorna as
permissões do perfil juntamente com o token.

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
  "expires_in": 300,
  "token_enriquecido": "eyJhbGci...",
  "data_expiracao_token_enriquecido": "2026-07-20T10:14:34-03:00"
}
```

`roles` vem no formato bruto do Keycloak (`realm_access`/`resource_access`),
extraído direto dos claims do access token — sem filtragem ou renomeação.
Depende dos protocol mappers configurados no client de login
(`KEYCLOAK_LOGIN_CLIENT_ID`); `admin-cli` não os inclui, `auto-servico-qa`
sim.

`token_enriquecido` **não é** o `access_token` OIDC do Keycloak — é um JWT
emitido pelo SME-Identidade-Token-Microsservico, com as claims de
perfis/permissões já embutidas para o cliente consumir sem precisar de
outra chamada. O token enriquecido carrega o contexto de autorização do
usuário e é obtido pelo Gateway junto ao
SME-Identidade-Token-Microsservico durante o fluxo de autenticação.

Se o usuário não tiver projeção no SME-Identidade-Token-Microsservico
(ou o serviço estiver fora do ar), o login **não falha** —
`token_enriquecido` e sua data de expiração não são retornados na
resposta.

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

## Níveis de acesso (real — Token-MS)

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/usuarios/{login}/perfis/` | Perfis de acesso do usuário |
| `GET` | `/usuarios/{login}/perfis/{perfil}/acesso/` | Token enriquecido + permissões do perfil |

Consulta avulsa — útil para recarregar perfis/permissões sem logar de
novo. `POST /login/` já traz tudo isso numa única resposta (ver seção
acima); estas rotas não são o único caminho para obter o token
enriquecido.

Ambas resolvem a conta do usuário no Keycloak (via
`keycloak_admin.obter_dados_usuario`, mesma normalização usada em
`GET /usuarios/{login}/dados/`).

`GET /usuarios/{login}/perfis/` consulta os perfis de acesso do usuário
no SME-Identidade-Token-Microsservico. Já
`GET /usuarios/{login}/perfis/{perfil}/acesso/` solicita ao
SME-Identidade-Token-Microsservico a geração do token enriquecido por
meio de `POST {TOKEN_MS_URL}/api/v1/token/enriquecido/{kc_user_id}/`,
via `apps.core.clientes.token_ms`.

`GET /perfis/{perfil}/acesso/` obtém do
SME-Identidade-Token-Microsservico o token enriquecido correspondente
ao perfil selecionado, incluindo
a claim `perfilSelecionado` (o `{perfil}` da URL) — diferente do token
composto no login, que ainda não tem um perfil selecionado.

**Erros:**

| Situação | Status |
|---|---|
| Login não encontrado no Keycloak | `204 No Content` (sem corpo) |
| Sem projeção para o usuário no Token-MS | `204 No Content` (sem corpo) |
| Token-MS não responde a tempo | `504` |
| Token-MS inacessível | `502` |

---

## Gestão de credencial (real — Keycloak)

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/alterar-senha/` | Define senha definitiva (não exige troca no próximo login) |
| `POST` | `/alterar-email/` | Atualiza e-mail e reabre a verificação |

Diferente das rotas de login, estas **já operam contra o Keycloak de
verdade** via `apps/autenticacao/keycloak_admin.py` (`KeycloakAdmin`, lib
`python-keycloak` — mesmo padrão de conexão do ETL). Gestão de credencial é
responsabilidade nativa do Keycloak: nenhum token de recuperação de senha é
gerado, armazenado ou validado por este serviço — todo o mecanismo (link
assinado, expiração, envio de e-mail) é do próprio Keycloak.

```json
// POST /alterar-senha/
{"login": "1234567", "senha": "novaSenha"}
```

```json
// POST /alterar-email/
{"login": "1234567", "email": "novo@sme.prefeitura.sp.gov.br"}
```

**Retorno de sucesso (`alterar-senha/`):**

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
| `TOKEN_MS_URL` | `http://token-ms:8000` | URL base do SME-Identidade-Token-Microsservico |
| `TOKEN_MS_TIMEOUT` | `10` | Timeout (segundos) das chamadas ao Token-MS |
| `API_KEY_TOKEN_MS` | — | Chave de serviço a serviço Gateway → Token-MS (deve corresponder ao `API_KEY` do Token-MS) |
| `API_KEY_TOKEN_MS_HEADER` | `X-API-Key` | Header onde a chave do Token-MS é enviada |

`KEYCLOAK_LOGIN_CLIENT_ID` é distinto de `KEYCLOAK_CLIENT_ID`: o primeiro
autentica usuário final (login), o segundo é usado só pela Admin API para
required actions. `auto-servico-qa` é confidencial (exige `client_secret`)
e é o client com os protocol mappers de roles configurados no realm
`COTIC`; `admin-cli` é público mas não inclui `realm_access`/
`resource_access` no token. Direct Access Grants foi habilitado
manualmente no `auto-servico-qa` via Admin API (não vem habilitado por
padrão em clients confidenciais).
