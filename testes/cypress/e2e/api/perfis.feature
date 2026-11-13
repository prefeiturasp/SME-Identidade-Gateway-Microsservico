# language: pt

Funcionalidade: API - Perfis

  Cenário: Validar consulta de perfis do usuário
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de perfis do usuário
    Então retorna o status 200
    E o retorno deve conter a lista de perfis

  Cenário: Validar RF e estrutura dos perfis do usuário
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de perfis do usuário
    Então retorna o status 200
    E o retorno deve conter o RF do usuário e perfis com estrutura válida

  Cenário: Validar consulta de perfis do usuário sem a API Key
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de perfis do usuário sem informar a API Key
    Então retorna o status 401

  Cenário: Validar consulta de perfis do usuário com API Key inválida
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de perfis do usuário com API Key inválida
    Então retorna o status 401

  Cenário: Validar consulta de dados de acesso por perfil
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de dados de acesso do perfil do usuário
    Então retorna o status 200
    E o retorno deve conter o token e as permissões do perfil

  Cenário: Validar estrutura das permissões do perfil do usuário
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de dados de acesso do perfil do usuário
    Então retorna o status 200
    E as permissões do perfil devem ter estrutura válida

  Cenário: Validar consulta de dados de acesso sem a API Key
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de dados de acesso do perfil do usuário sem informar a API Key
    Então retorna o status 401

  Cenário: Validar consulta de dados de acesso com API Key inválida
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de dados de acesso do perfil do usuário com API Key inválida
    Então retorna o status 401
