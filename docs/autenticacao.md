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
real contra o Keycloak. Numa única resposta, também busca a projeção no
SME-Identidade-Token-Microsservico e compõe o **token enriquecido** — o
Gateway é o próprio auth-gateway-ms da arquitetura da plataforma (ver
`apps.autenticacao.token_enriquecido`), não é necessária uma segunda
chamada para obter o token. `perfis`/`permissoes` não vêm soltos no
corpo — já estão embutidos nas claims do `token_enriquecido`; para obtê-
los sem decodificar o JWT, usar `GET /usuarios/{login}/perfis/` ou
`GET /usuarios/{login}/perfis/{perfil}/acesso/`.

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
próprio do Gateway, assinado com `JWT_ENRIQUECIDO_SECRET` (HS256), com as
claims de perfis/permissões já embutidas para o cliente consumir sem
precisar de outra chamada. Cada sistema integrado ao SME-Identidade
implementa seu próprio fluxo de login/consumo — o token enriquecido é o
artefato que carrega o contexto de autorização completo do usuário para
esse consumo. O Token-MS não emite JWT (só projeta claims); quem monta e
assina é o próprio Gateway. Ver claims em "Níveis de acesso" abaixo.

Se o usuário não tiver projeção no Token-MS (ou o serviço estiver fora do
ar), o login **não falha** — `perfis`/`permissoes` vêm vazios e
`token_enriquecido` é composto só com as claims do Keycloak.

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
`GET /usuarios/{login}/dados/`) e consultam a projeção real em
`GET {TOKEN_MS_URL}/api/v1/perfis/{kc_user_id}/` no
SME-Identidade-Token-Microsservico, via `apps.core.clientes.token_ms`.

`GET /perfis/{perfil}/acesso/` compõe o token enriquecido com
`apps.autenticacao.token_enriquecido.compor_token_enriquecido`, incluindo
a claim `perfilSelecionado` (o `{perfil}` da URL) — diferente do token
composto no login, que ainda não tem um perfil selecionado.

**Claims do token enriquecido:**

| Claim | Origem |
|---|---|
| `sub`, `preferred_username`, `email` | Keycloak |
| `rf`, `cpf` | Keycloak (sobrescrito pela projeção do Token-MS, se houver) |
| `nome`, `situacao`, `dre_codigo`, `contrato_externo` | Token-MS (ausentes se não houver projeção) |
| `perfis`, `permissoes` | Token-MS (listas vazias se não houver projeção) |
| `perfilSelecionado` | Só em `GET /perfis/{perfil}/acesso/`, ausente no login |
| `iss` | Sempre `"sme-identidade-gateway"` |
| `iat`, `exp` | Emissão e expiração (`JWT_ENRIQUECIDO_TTL_SEGUNDOS`) |

**Erros:**

| Situação | Status |
|---|---|
| Login não encontrado no Keycloak | `204 No Content` (sem corpo) |
| Sem projeção para o usuário no Token-MS | `204 No Content` (sem corpo) |
| Token-MS não responde a tempo | `504` |
| Token-MS inacessível | `502` |

### Como decodificar o token enriquecido

O `token_enriquecido`/`token` retornado por `POST /login/` e
`GET /perfis/{perfil}/acesso/` é um JWT assinado com `JWT_ENRIQUECIDO_SECRET`
(`HS256` por padrão) — **não** é o `access_token` do Keycloak, então não
valida contra o JWKS do Keycloak. Quem consome precisa da mesma chave
configurada no Gateway para verificar a assinatura.

**Python (`PyJWT`, mesma lib usada pelo Gateway):**

```python
import jwt

claims = jwt.decode(
    token_enriquecido,
    "<valor de JWT_ENRIQUECIDO_SECRET>",
    algorithms=["HS256"],  # ou o valor de JWT_ENRIQUECIDO_ALGORITMO
)
print(claims["rf"], claims["perfis"], claims["permissoes"])
```

Sem a chave (ex.: só inspecionar o payload durante desenvolvimento, sem
verificar a assinatura), usar `jwt.decode(token, options={"verify_signature": False})`
— **nunca** fazer isso em produção antes de confiar nos dados.

**Node.js (`jsonwebtoken`):**

```js
const jwt = require("jsonwebtoken");

const claims = jwt.verify(tokenEnriquecido, process.env.JWT_ENRIQUECIDO_SECRET, {
  algorithms: ["HS256"],
});
console.log(claims.rf, claims.perfis, claims.permissoes);
```

**.NET (`System.IdentityModel.Tokens.Jwt`):**

```csharp
var handler = new JwtSecurityTokenHandler();
var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtEnriquecidoSecret));
var parametros = new TokenValidationParameters
{
    ValidateIssuerSigningKey = true,
    IssuerSigningKey = key,
    ValidateIssuer = true,
    ValidIssuer = "sme-identidade-gateway",
    ValidateAudience = false,
};
var principal = handler.ValidateToken(tokenEnriquecido, parametros, out _);
```

**Linha de comando (inspeção rápida, sem verificar assinatura):**

```bash
echo "$TOKEN_ENRIQUECIDO" | cut -d. -f2 | base64 -d 2>/dev/null | python3 -m json.tool
```

O payload base64 do meio do JWT (segunda parte, entre pontos) decodifica
para o JSON das claims — útil para conferir o conteúdo em debug local, mas
não substitui a verificação de assinatura em produção.

**Debug visual:** colar o token em [jwt.io](https://jwt.io) mostra o
payload decodificado; para verificar a assinatura lá, informar o mesmo
valor de `JWT_ENRIQUECIDO_SECRET` no campo "Verify Signature" — **evitar
colar tokens de produção em serviços externos**, usar só em ambiente local
com secret de desenvolvimento.

Ver a tabela de claims acima para o significado de cada campo do payload.

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
| `JWT_ENRIQUECIDO_SECRET` | — | Chave de assinatura do token enriquecido (HMAC) — gerar um secret dedicado, nunca reaproveitar `DJANGO_SECRET_KEY` |
| `JWT_ENRIQUECIDO_ALGORITMO` | `HS256` | Algoritmo de assinatura do token enriquecido |
| `JWT_ENRIQUECIDO_TTL_SEGUNDOS` | `28800` (8h) | Tempo de vida do token enriquecido |

`KEYCLOAK_LOGIN_CLIENT_ID` é distinto de `KEYCLOAK_CLIENT_ID`: o primeiro
autentica usuário final (login), o segundo é usado só pela Admin API para
required actions. `auto-servico-qa` é confidencial (exige `client_secret`)
e é o client com os protocol mappers de roles configurados no realm
`COTIC`; `admin-cli` é público mas não inclui `realm_access`/
`resource_access` no token. Direct Access Grants foi habilitado
manualmente no `auto-servico-qa` via Admin API (não vem habilitado por
padrão em clients confidenciais).
