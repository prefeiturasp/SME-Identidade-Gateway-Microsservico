Referência de código
====================

Esta página publica as docstrings dos principais módulos do projeto. Detalhes
de endpoints, status HTTP e contratos externos devem permanecer no OpenAPI ou
em páginas técnicas específicas.

Core
----

.. automodule:: apps.core.api.views
   :members:

.. automodule:: apps.core.api.serializers
   :members:

.. automodule:: apps.core.api.urls
   :members:

.. automodule:: apps.core.api_clients
   :members:

.. automodule:: apps.core.http_client
   :members:

.. automodule:: apps.core.http
   :members:

Autenticação
------------

.. automodule:: apps.autenticacao.api_key
   :members:

.. automodule:: apps.autenticacao.keycloak_admin
   :members:

.. automodule:: apps.autenticacao.services
   :members:

.. automodule:: apps.autenticacao.gatilho_auditoria
   :members:

.. automodule:: apps.autenticacao.api.views
   :members:

.. automodule:: apps.autenticacao.api.views_credenciais
   :members:

.. automodule:: apps.autenticacao.api.serializers
   :members:

EOL Autenticação
---------------------

.. automodule:: apps.eol_autenticacao.api.views
   :members:

.. automodule:: apps.eol_autenticacao.services.recuperacao_senha
   :members:

Provedores de identidade
------------------------------

.. automodule:: apps.provedores.contratos
   :members: ProvedorIdentidade

.. autoclass:: apps.provedores.contratos.UsuarioIdentidade

.. automodule:: apps.provedores.excecoes
   :members:

.. automodule:: apps.provedores.fabrica
   :members:

.. automodule:: apps.provedores.keycloak
   :members:

Gestão de Usuário
------------------

.. automodule:: apps.gestao_usuario.cliente_etl
   :members:

.. automodule:: apps.gestao_usuario.api.views
   :members:

.. automodule:: apps.gestao_usuario.api.serializers
   :members:

EOL Autenticação SGP
---------------------

.. automodule:: apps.eol_autenticacao_sgp.api.views
   :members:

.. automodule:: apps.eol_autenticacao_sgp.api.serializers
   :members:

.. automodule:: apps.eol_autenticacao_sgp.services
   :members:
