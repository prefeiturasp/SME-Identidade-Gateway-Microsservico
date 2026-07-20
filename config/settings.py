"""Configuração Django do SME-Identidade-Gateway-Microsservico."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY", "django-inseguro-apenas-desenvolvimento"
)
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "rest_framework",
    "drf_spectacular",
    "apps.core",
    "apps.autenticacao",
    "apps.gestao_usuario",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.autenticacao.api_key.AutenticacaoApiKey",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# Autenticação de serviço a serviço (mesmo padrão do ETL e esperado
# no Token-MS): header configurável comparado a uma chave fixa.
API_KEY = os.getenv("API_KEY", "")
API_KEY_HEADER = os.getenv("API_KEY_HEADER", "X-API-Key")

# SME-Identidade-Token-Microsservico — destino do roteamento de
# perfis/níveis de acesso (apps.autenticacao) e do health check
# estendido (apps.core.clientes.token_ms).
TOKEN_MS_URL = os.getenv("TOKEN_MS_URL", "http://token-ms:8000")
TOKEN_MS_TIMEOUT = float(os.getenv("TOKEN_MS_TIMEOUT", "10"))

# API Key própria para a chamada de serviço Gateway → Token-MS —
# distinta da API_KEY que os clientes usam para chamar o Gateway.
API_KEY_TOKEN_MS = os.getenv("API_KEY_TOKEN_MS", "")
API_KEY_TOKEN_MS_HEADER = os.getenv("API_KEY_TOKEN_MS_HEADER", "X-API-Key")

# Keycloak Admin API — usado nas rotas de gestão de senha/e-mail
# (recuperação de senha, alteração de senha, alteração de e-mail) e
# para resolver a conta do usuário (login/dados). Mesmas variáveis de
# ambiente já usadas no SME-Identidade-ETL, para manter um único
# padrão de configuração de Keycloak na plataforma.
KEYCLOAK_URL_SERVIDOR = os.getenv(
    "KEYCLOAK_URL_SERVIDOR", "https://localhost:8080/"
)
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "COTIC")
KEYCLOAK_USUARIO_ADMIN = os.getenv("KEYCLOAK_USUARIO_ADMIN", "admin")
KEYCLOAK_SENHA_ADMIN = os.getenv("KEYCLOAK_SENHA_ADMIN", "admin")
KEYCLOAK_VERIFICAR_SSL = (
    os.getenv("KEYCLOAK_VERIFICAR_SSL", "true").lower() == "true"
)

# Token enriquecido — JWT próprio do Gateway (auth-gateway-ms), composto
# a partir das claims do Keycloak + projeção do Token-MS. Assinado com
# chave própria (HS256), não é o access_token OIDC do Keycloak — usado
# para compatibilidade com sistemas legados que esperam "um token" da
# API/EOL. Ver apps.autenticacao.token_enriquecido.
JWT_ENRIQUECIDO_SECRET = os.getenv("JWT_ENRIQUECIDO_SECRET", "")
JWT_ENRIQUECIDO_ALGORITMO = os.getenv("JWT_ENRIQUECIDO_ALGORITMO", "HS256")
JWT_ENRIQUECIDO_TTL_SEGUNDOS = int(
    os.getenv("JWT_ENRIQUECIDO_TTL_SEGUNDOS", "28800")
)

# Client OIDC usado para autenticar usuário final via grant type
# password (LoginView) e como client_id nas required actions de
# credencial (send_update_account/send_verify_email) — precisa ter
# "Direct Access Grants" habilitado e existir de fato no realm.
# auto-servico-qa é o client com os protocol mappers de
# realm_access/resource_access (roles) configurados — confidencial,
# exige client_secret. Um client dedicado "identidade-gateway" chegou
# a ser cogitado para as required actions, mas não existe no realm
# COTIC de QA (KeycloakPutError: "Client doesn't exist") — reusar o
# client de login evita depender de um cadastro extra no Keycloak.
KEYCLOAK_LOGIN_CLIENT_ID = os.getenv(
    "KEYCLOAK_LOGIN_CLIENT_ID", "auto-servico-qa"
)
KEYCLOAK_LOGIN_CLIENT_SECRET = os.getenv("KEYCLOAK_LOGIN_CLIENT_SECRET", "")

# SME-Identidade-ETL — destino da gestão de usuário (criação,
# sincronização, concessão de acesso e consulta de identidade). O
# Gateway não fala com o Keycloak Admin API para provisionamento de
# identidade; delega inteiramente ao ETL, que já tem essa lógica.
# Inclui o prefixo "/identidade-etl" — é parte do roteamento do
# próprio ETL (config/urls.py:_PREFIXO), não um path de proxy externo.
ETL_URL = os.getenv("ETL_URL", "http://identidade-etl:8000/identidade-etl")
ETL_TIMEOUT = float(os.getenv("ETL_TIMEOUT", "30"))

# API Key própria para a chamada de serviço Gateway → ETL — distinta
# da API_KEY que os clientes usam para chamar o Gateway.
API_KEY_ETL = os.getenv("API_KEY_ETL", "")
API_KEY_ETL_HEADER = os.getenv("API_KEY_ETL_HEADER", "X-API-Key")
