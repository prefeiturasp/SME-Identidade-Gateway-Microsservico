# SME-Identidade-Gateway-Microsservico

O SME-Identidade-Gateway-Microsservico é responsável pela centralização das capacidades de autenticação, validação de identidade e propagação segura de contexto autenticado entre aplicações e microsserviços da SME-SP.

Atuando como camada transversal de autenticação, o serviço integra a plataforma aos provedores de identidade corporativos, padronizando os fluxos de acesso e garantindo a validação consistente de credenciais e tokens.

Além da autenticação, o microsserviço assegura a propagação segura do contexto autenticado entre os componentes da arquitetura, contribuindo para a rastreabilidade, observabilidade e aplicação uniforme das políticas de segurança da plataforma.

## Estrutura do repositório

```
.
├── apps/
│   ├── core/           # cliente HTTP
├── config/             # settings, urls, wsgi
├── requirements/
│   ├── base.txt        # dependências de produção
│   └── local.txt       # base + ferramentas de desenvolvimento
└── manage.py
```

### apps/core

| Módulo | Responsabilidade |
|---|---|
| `api/views.py` | Endpoints da aplicação, incluindo o health check do serviço |
| `api/serializers.py` | Serialização e validação de dados de entrada e saída |
| `api/urls.py` | Registro e roteamento das URLs da aplicação |

## Requisitos

- Python 3.12+
- Docker e Docker Compose

## Configuração do ambiente

```bash
cp .env.example .env
make build
make run
```

**Geral**

| Variável | Padrão | Descrição |
|---|---|---|
| `DJANGO_SECRET_KEY` | — | Chave secreta do Django |
| `DJANGO_DEBUG` | `1` | Ativa o modo debug (`0` em produção) |
| `DJANGO_ALLOWED_HOSTS` | `*` | Hosts permitidos, separados por vírgula |

## Atalhos Make

Use `make help` para listar todos os comandos disponíveis. Os principais:

**Ambiente**

| Comando | Descrição |
|---|---|
| `make run` | Sobe o containers em modo dev (porta 8002) |
| `make build` | Rebuild da imagem dev |
| `make stop` | Para e remove containers |

**Testes**

| Comando | Descrição |
|---|---|
| `make test` | Suite completa com cobertura ≥ 80% |
| `make test-core` | Apenas `apps.core` |

**Qualidade**

| Comando | Descrição |
|---|---|
| `make lint` | ruff + black + isort + mypy |
| `make coverage` | Relatório HTML em `docs/_cov/` |
| `make schema` | Gera schema OpenAPI em `schema.yml` |
| `make docs` | Gera documentação Sphinx em `docs/_build/html/` |

## Endpoints

Consulte o Swagger em `/api/v1/docs/` para a lista completa de rotas com parâmetros e exemplos de resposta.