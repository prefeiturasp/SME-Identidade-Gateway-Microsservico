# language: pt

Funcionalidade: API - Consulta de acesso do perfil

  Cenário: Validar que o endpoint de consulta de acesso do perfil exige API Key
    Quando consulto endpoint de consulta de acesso do perfil sem API Key
    Então endpoint de consulta de acesso do perfil rejeita requisicao sem API Key

  Cenário: Validar consulta de acesso de perfil sem login
    Dado que possuo acesso à API de autenticação
    Quando consulto endpoint de consulta de acesso do perfil sem informar login
    Então retorna o status 404