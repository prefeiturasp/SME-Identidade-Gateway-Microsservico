# language: pt

Funcionalidade: API - Concessão de acesso

  Cenário: Validar endpoint concessão de acesso
    Quando consulto o endpoint de concessão de acesso
    Então a resposta de concessão de acesso deve ser válida

  Cenário: Validar concessão de acesso sem roles
    Dado que possuo acesso à API de autenticação
    Quando envio concessão de acesso sem roles
    Então a resposta de concessão de acesso deve ser válida

