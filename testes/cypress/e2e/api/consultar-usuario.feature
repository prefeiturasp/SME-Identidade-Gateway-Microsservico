# language: pt

Funcionalidade: API - Consulta de usuário

  Cenário: Validar endpoint consulta de usuário
    Quando consulto o endpoint de consulta de usuário
    Então a resposta de consulta de usuário deve ser válida

  Cenário: Validar consulta de usuário com API Key inválida
    Dado que possuo acesso à API de autenticação
    Quando consulto endpoint de consulta de usuário com API Key inválida
    Então retorna o status 401

