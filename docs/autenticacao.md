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
| `encerrar_sessao(refresh_token)` | Chama `KeycloakOpenID.logout()` com o refresh token — ver seção Logout, abaixo |
| `decodificar_claims_token(token)` | Decodifica o payload de um JWT (access ou refresh token) sem validar assinatura — usada para extrair `roles` em `autenticar` e o `sub` (kc_user_id) em `encerrar_sessao` |

---

## Logout (real — Keycloak)

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/logout/` | Encerra a sessão associada a um refresh token |

O Gateway não mantém sessão própria — encerrar a sessão do usuário depende de repassar ao
Keycloak o `refresh_token` obtido no login.

```json
// POST /logout/
{"refresh_token": "eyJhbGci..."}
```

```json
// 200
{"situacao": "sessao_encerrada"}
```

Se o token já estiver inválido ou expirado, a resposta continua `200` — o resultado prático
(sessão encerrada) já é o mesmo, então o cliente não precisa distinguir os dois casos.

**Erros:**

| Situação | Status |
|---|---|
| Sem `refresh_token` no corpo | `400` |
| Sem `X-API-Key` | `401` |

---

## Níveis de acesso (real — Token-MS)

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/usuarios/{login}/perfis/` | Perfis de acesso do usuário |
| `GET` | `/usuarios/{login}/sistemas/` | Sistemas distintos que o usuário acessa |
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

`GET /usuarios/{login}/sistemas/` consulta a lista de sistemas
distintos aos quais o usuário tem acesso, obtida do
SME-Identidade-Token-Microsservico via
`GET {TOKEN_MS_URL}/api/v1/perfis/{kc_user_id}/sistemas/`. Existe
porque o Token-MS não deduplica sistemas em `GET /perfis/{usuario_id}/`
(cada item de `permissoes` traz seu próprio `sistema_id`/`sistema_nome`,
repetido por módulo) — este endpoint expõe essa lista já consolidada,
sem exigir que o consumidor faça a deduplicação por conta própria.

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

## Aviso de atividade ao Audit-MS

`POST /login/`, `POST /logout/`, `POST /alterar-senha/` e `POST /alterar-email/` avisam o
SME-Identidade-Audit-Microsservico de que houve atividade do usuário
(`apps/autenticacao/gatilho_auditoria.py`).

O `usuario_id` do aviso vem de fontes diferentes conforme a rota: em `/login/`, da conta resolvida
por `keycloak_admin.autenticar`; em `/logout/`, extraído do próprio `refresh_token` (função
`decodificar_claims_token`) — o endpoint de logout não recebe login/senha, só o token; em
`/alterar-senha/` e `/alterar-email/`, resolvido a partir do `login` recebido
(`disparar_gatilho_por_login`).

O que trafega é apenas `{"realm", "usuario_id"}` — **não** um evento de
auditoria. Dois produtores de evento gerariam timestamps distintos para a
mesma atividade, e a deduplicação no destino teria de reconciliar formatos
divergentes; com o aviso mínimo, o Keycloak segue como origem única do dado.
O aviso apenas antecipa a leitura, que aconteceria de todo modo no ciclo
agendado do Audit-MS.

O disparo é acessório ao fluxo que o usuário está esperando: falha de rede,
timeout ou destino fora do ar são engolidos, no mesmo padrão de degradação
graciosa já usado quando o token enriquecido não pode ser obtido. Login e
trocas de credencial continuam respondendo normalmente com o Audit-MS fora do
ar.

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
| `AUDIT_MS_URL` | `http://audit-ms:8000/identidade-auditoria` | URL base do SME-Identidade-Audit-Microsservico |
| `AUDIT_MS_TIMEOUT` | `2` | Timeout (segundos) do aviso de atividade — curto porque o disparo acontece dentro de fluxos que o usuário aguarda |
| `API_KEY_AUDIT_MS` | — | Chave de serviço a serviço Gateway → Audit-MS (deve corresponder ao `API_KEY` do Audit-MS) |
| `API_KEY_AUDIT_MS_HEADER` | `X-API-Key` | Header onde a chave do Audit-MS é enviada |

`KEYCLOAK_LOGIN_CLIENT_ID` é distinto de `KEYCLOAK_CLIENT_ID`: o primeiro
autentica usuário final (login), o segundo é usado só pela Admin API para
required actions. `auto-servico-qa` é confidencial (exige `client_secret`)
e é o client com os protocol mappers de roles configurados no realm
`COTIC`; `admin-cli` é público mas não inclui `realm_access`/
`resource_access` no token. Direct Access Grants foi habilitado
manualmente no `auto-servico-qa` via Admin API (não vem habilitado por
padrão em clients confidenciais).

---

## Logout global (endpoint de recepção — SME-Identidade-SSO-Microsservico)

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/logout-notificacao/` | Recebe a notificação de logout global disparada pelo SSO-MS |

Endpoint de **teste E2E** do mecanismo de logout global do
SME-Identidade-SSO-Microsservico: quando uma sessão compartilhada é
encerrada, o SSO-MS notifica em paralelo cada sistema conectado (ver
`docs/arquitetura/fluxo_logout_global.md` no repositório do SSO-MS). O
Gateway não mantém sessão própria (ver seção "Logout" acima), então
esta view apenas registra o recebimento (`sessao_id`, `login`,
`kc_user_id`) e confirma — não invalida nada real localmente.

---

## Autenticação entre clients (real — Keycloak)

| Método | Endpoint                 | Descrição                                     |
| ------ | ------------------------ | --------------------------------------------- |
| `POST` | `/cliente/login/`        | Autentica um client via Client Credentials    |
| `POST` | `/cliente/validar-token/`| Valida o access token emitido pelo Keycloak   |

Fluxo destinado à autenticação **machine-to-machine**, sem participação de
usuário, senha de usuário ou sessão SSO. O sistema consumidor se autentica
utilizando o `client_id` e o `client_secret` cadastrados no Keycloak.

O fluxo utiliza o grant type `client_credentials` e o access token emitido
representa a **Service Account** associada ao client.

Para utilizar esse fluxo, o client deve possuir autenticação de client
habilitada e estar configurado no Keycloak com **Service Accounts Roles**
habilitado.

### Obtenção do access token

```json
// POST /cliente/login/
{
  "client_id": "sistema-consumidor",
  "client_secret": "..."
}
```

O `client_id` corresponde ao identificador configurado no campo
**Client ID** do Keycloak, e não ao UUID interno do client.

O Gateway instancia `KeycloakOpenID` com as credenciais recebidas e solicita
o token ao Keycloak utilizando:

```text
grant_type=client_credentials
```

Não há resolução de usuário nem utilização do fluxo de login via
`password`. Portanto, este mecanismo é independente da autenticação de
usuários existente em `POST /login/`.

Em caso de sucesso:

```json
// 200
{
  "access_token": "eyJhbGci...",
  "token_type": "Bearer",
  "expires_in": 300
}
```

`access_token` é o token OIDC emitido diretamente pelo Keycloak para a
Service Account do client.

`expires_in` representa o tempo de validade do token, em segundos, e deve
ser considerado pelo sistema consumidor para controlar sua expiração e
solicitar um novo token quando necessário.

O token deve ser enviado às APIs protegidas utilizando o header HTTP:

```text
Authorization: Bearer <access_token>
```

Diferente do `token_enriquecido` utilizado no fluxo de autenticação de
usuários, este token é emitido diretamente pelo Keycloak e representa o
sistema autenticado, não um usuário final.

### Identificação do sistema consumidor

A identidade do sistema responsável pela chamada está vinculada ao client
autenticado no Keycloak.

Cada sistema consumidor deve possuir seu próprio `client_id`, permitindo
identificar a origem da chamada pelas claims presentes no access token,
conforme a configuração do realm e dos protocol mappers.

Não é necessário enviar um identificador de sistema separado no fluxo de
autenticação, evitando divergências entre a identidade informada pela
aplicação e a identidade registrada no token.

### Validação do access token

O endpoint de validação recebe apenas o access token:

```json
// POST /cliente/validar-token/
{
  "token": "eyJhbGci..."
}
```

A validação não exige o reenvio de `client_id` ou `client_secret`.

O Gateway valida o JWT utilizando as configurações e chaves públicas do
realm do Keycloak. Dessa forma, não é necessário armazenar no Gateway as
credenciais dos sistemas consumidores para realizar a validação dos tokens.

Token válido:

```json
// 200
{
  "valido": true,
  "expirado": false,
  "claims": {
    "exp": 1788969000,
    "iat": 1788968700,
    "azp": "sistema-consumidor"
  }
}
```

Token expirado:

```json
// 200
{
  "valido": false,
  "expirado": true,
  "claims": {},
  "detalhe": "Token expirado."
}
```

Token inválido:

```json
// 200
{
  "valido": false,
  "expirado": false,
  "claims": {},
  "detalhe": "Token inválido."
}
```

A validação de um token inválido ou expirado retorna `200` porque a
requisição de validação foi processada corretamente. O estado do token é
informado pelos campos `valido` e `expirado`.

Isso é diferente do uso do token em uma API protegida: caso um access token
inválido ou expirado seja utilizado para acessar um recurso que exige
autenticação, a API destinatária deve rejeitar a chamada conforme sua
política de segurança.

### Segurança das credenciais

O `client_secret` é utilizado somente durante a solicitação do access token
e não é retornado na resposta.

O Gateway também não mantém um cadastro local dos secrets dos sistemas
consumidores. Dessa forma, a quantidade de clients cadastrados no Keycloak
não exige replicação das credenciais no ambiente ou nas configurações do
`gateway-ms`.

As credenciais não devem ser armazenadas diretamente no código-fonte dos
sistemas consumidores. Cada aplicação é responsável por manter seu próprio
`client_secret` em mecanismo seguro de configuração ou gerenciamento de
segredos.

### Fluxo de autenticação

```text
Sistema consumidor
        |
        | client_id + client_secret
        v
Gateway
        |
        | grant_type=client_credentials
        v
Keycloak
        |
        | access_token
        | token_type
        | expires_in
        v
Gateway
        |
        v
Sistema consumidor
        |
        | Authorization: Bearer <access_token>
        v
API protegida
```

Este fluxo é independente do login de usuários e não altera o funcionamento
de `POST /login/`, `POST /logout/` ou do token enriquecido gerado pelo
SME-Identidade-Token-Microsservico.