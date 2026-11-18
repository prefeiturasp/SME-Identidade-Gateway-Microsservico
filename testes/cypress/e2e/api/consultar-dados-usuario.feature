# language: pt

Funcionalidade: API - Consulta de dados do usuário

  Cenário: Validar que o endpoint de consulta de dados do usuário exige API Key
    Quando consulto endpoint de consulta de dados do usuário sem API Key
    Então endpoint de consulta de dados do usuário rejeita requisicao sem API Key