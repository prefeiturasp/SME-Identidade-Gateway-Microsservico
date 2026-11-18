# language: pt

Funcionalidade: API - Sincronização de usuário

  Cenário: Validar endpoint sincronização de usuário
    Quando consulto o endpoint de sincronização de usuário
    Então a resposta de sincronização de usuário deve ser válida

  Cenário: Validar sincronização sem identificador
    Dado que possuo acesso à API de autenticação
    Quando envio sincronização sem identificador
    Então a resposta de sincronização de usuário deve ser válida

