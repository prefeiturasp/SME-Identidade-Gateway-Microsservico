# language: pt

Funcionalidade: API - Validação de token de cliente

  Cenário: Validar endpoint validação de token de cliente
    Quando consulto o endpoint de validação de token de cliente
    Então a resposta de validação de token de cliente deve ser válida

  Cenário: Validar rejeição de token de cliente vazio
    Dado que possuo acesso à API de autenticação
    Quando valido token de cliente vazio
    Então a resposta de validação de token de cliente deve ser válida

