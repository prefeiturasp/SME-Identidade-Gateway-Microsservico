# language: pt

Funcionalidade: API - Perfis

  Cenário: Validar consulta de perfis do usuário
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de perfis do usuário
    Então retorna o status 200
    E o retorno deve conter a lista de perfis

  Cenário: Validar consulta de dados de acesso por perfil
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de dados de acesso do perfil do usuário
    Então retorna o status 200
    E o retorno deve conter o token e as permissões do perfil
