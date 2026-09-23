# Gestão de Usuário

Definido em `apps/gestao_usuario/`. Camada fina de entrada: autentica a
requisição via `AutenticacaoApiKey`, valida o payload e repassa ao
SME-Identidade-ETL, que é quem de fato fala com o Keycloak Admin API.
**Nenhuma lógica de upsert, idempotência ou provisionamento é
reimplementada aqui** — o Gateway só roteia.

```
Cliente → Gateway (autentica, valida entrada, roteia) → ETL (lógica real, fala com Keycloak) → Keycloak
```

Rotas registradas sob `identidade-gateway/api/v1/usuarios/`.

---

## Endpoints

| Método | Endpoint | Repassa para (ETL) |
|---|---|---|
| `POST` | `/` | `POST /identidade-etl/api/v1/etl/usuario/criar/` |
| `POST` | `/sincronizar/` | `POST /identidade-etl/api/v1/etl/usuario/sincronizar/` |
| `POST` | `/conceder-acesso/` | `POST /identidade-etl/api/v1/etl/usuario/conceder-acesso/` |
| `GET` | `/consultar/` | `GET /identidade-etl/api/v1/etl/identidades/consultar/` |

Os nomes de campo dos payloads espelham exatamente os serializers
equivalentes do ETL — não há tradução de contrato.

---

## Criar usuário

Cria um usuário no Keycloak a partir de dados diretos — **não depende do
usuário já existir no CoreSSO**. `sistema`/`roles` são opcionais: quando
informados juntos, o ETL concede o acesso na mesma chamada de criação.

```json
{
  "nome": "Fulano de Tal",
  "cpf": "12345678900",
  "email": "fulano@externo.com",
  "tipo_usuario": "terceiro",
  "sistema": 1008,
  "roles": ["COTIC"],
  "realm": "sme-apps"
}
```

Validações antes de chamar o ETL:

- É exigido ao menos `cpf` ou `rf`
- `sistema` e `roles` devem vir juntos, ou nenhum dos dois — informar
  apenas um dos dois retorna `400` sem chamar o ETL

**Retorno (exemplo com concessão de acesso):**

```json
{
  "acao": "criado",
  "kc_user_id": "6dbda0a5-...",
  "hash_conteudo": "42e9e153...",
  "sistema": "Auto Serviço",
  "client_id": "auto-servico-qa",
  "roles_atribuidos": ["COTIC"],
  "roles_nao_encontrados": [],
  "erros": 0
}
```

---

## Sincronizar usuário

Sincroniza um usuário **existente no CoreSSO** com o Keycloak, atribuindo
todos os roles de todos os sistemas aos quais ele já pertence.

```json
{"identificador": "1234567", "realm": "sme-apps"}
```

---

## Conceder acesso

Concede acesso a um sistema e roles específicos, independentemente dos
vínculos reais no CoreSSO.

```json
{"identificador": "1234567", "sistema": 1008, "roles": ["COTIC"]}
```

---

## Consultar identidade

Consulta a conta do usuário **diretamente no Keycloak** (o ETL repassa
para `identidades/consultar/`, que busca via Keycloak Admin API — não é
mais uma leitura de cache local). Reflete o estado real,
independentemente de qual rota criou o usuário.

```
GET /consultar/?cpf=12345678900
GET /consultar/?rf=1234567
GET /consultar/?email=fulano@sme.sp.gov.br
```

**Retorno:**

```json
[
  {
    "kc_user_id": "5c29cc47-...",
    "username": "7376065",
    "nome": "MONICA CARVALHO TANG",
    "email": "monica.tang@sme.prefeitura.sp.gov.br",
    "ativo": true,
    "cpf": "26930618810",
    "rf": "7376065",
    "kc_url": "https://kc/.../users/.../settings"
  }
]
```

---

## Tratamento de erros de comunicação

Todas as views tratam falhas ao chamar o ETL:

| Situação | Status retornado |
|---|---|
| ETL responde com erro (ex.: usuário não encontrado no CoreSSO) | Status/corpo do ETL repassado como veio |
| ETL não responde a tempo | `504` |
| ETL inacessível (conexão recusada) | `502` |

---

## Configuração

| Variável | Padrão | Descrição |
|---|---|---|
| `ETL_URL` | `http://identidade-etl:8000` | URL base do SME-Identidade-ETL |
| `ETL_TIMEOUT` | `30` | Timeout em segundos das chamadas ao ETL |
| `API_KEY_ETL` | — | API Key própria da comunicação Gateway → ETL |
| `API_KEY_ETL_HEADER` | `X-API-Key` | Header onde a chave é enviada ao ETL |

`API_KEY_ETL` é distinta da `API_KEY` que os clientes usam para chamar o
Gateway — deve corresponder ao `API_KEY` configurado no SME-Identidade-ETL.
