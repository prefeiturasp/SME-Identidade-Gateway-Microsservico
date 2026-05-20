# SME-Identidade-Gateway-Microsservico

Microsserviço de autenticação centralizada da plataforma SME-Identidade.
Suporta três fluxos:

1. **OIDC moderno** — proxy autenticado contra o Keycloak (`/api/v1/oidc/*`),
   com enriquecimento de claims via `token-ms`.
2. **Legado .NET / API EOL** — ponte com shape de body compatível
   (`POST /api/v1/autenticacao`, `GET /autenticacaoSgp/...`) que emite JWTs
   no formato esperado pelos sistemas em migração.
3. **M2M (Client Credentials Grant)** — `/api/v1/m2m/token/` faz o grant via
   Keycloak e mantém um cache curto por par `(client_id, scope, audience)`.

Stack: Django 5 + DRF + httpx + django-redis (KeyDB) + Postgres.

## Rodar localmente

```bash
cp .env.example .env
docker compose up -d
curl -s http://localhost:8002/api/health/
curl -s http://localhost:8002/api/docs/
```

## Testes

```bash
pip install -r requirements.txt
pytest
# 38 testes, cobertura ~93%
```

Ver `pytest.ini` para o gate de cobertura (`--cov-fail-under=90`).

## Endpoints

| Método | Rota | Descrição |
| ------ | ---- | --------- |
| GET  | `/api/health/` | liveness |
| GET  | `/api/health/ready/` | readiness |
| POST | `/api/v1/oidc/token/` | password grant (legado moderno) |
| POST | `/api/v1/oidc/refresh/` | refresh token |
| POST | `/api/v1/oidc/introspect/` | introspection |
| POST | `/api/v1/oidc/logout/` | logout backchannel |
| GET  | `/api/v1/oidc/.well-known/openid-configuration` | discovery proxy |
| GET  | `/api/v1/oidc/certs/` | JWKS proxy |
| POST | `/api/v1/autenticacao` | login legado (BODY1 / Endpoint1) |
| GET  | `/api/v1/autenticacaoSgp/CarregarPerfisPorLogin/{login}` | perfis (BODY3) |
| GET  | `/api/v1/autenticacaoSgp/{login}/dados` | dados do usuário (BODY4) |
| GET  | `/api/v1/autenticacaoSgp/CarregarDadosAcesso/usuarios/{id}/perfis/{perfilId}` | JWT legado |
| POST | `/api/v1/m2m/token/` | client credentials |
| POST | `/api/v1/m2m/introspect/` | introspect M2M |
