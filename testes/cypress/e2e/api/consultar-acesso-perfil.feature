# language: pt

Funcionalidade: API - Consulta de acesso do perfil

  Cenário: Validar que o endpoint de consulta de acesso do perfil exige API Key
    Quando consulto endpoint de consulta de acesso do perfil sem API Key
    Então endpoint de consulta de acesso do perfil rejeita requisicao sem API Key