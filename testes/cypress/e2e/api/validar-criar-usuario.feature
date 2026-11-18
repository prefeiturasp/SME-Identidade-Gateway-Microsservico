# language: pt

Funcionalidade: API - Criação de usuário

  Cenário: Validar endpoint criação de usuário
    Quando consulto o endpoint de criação de usuário
    Então a resposta de criação de usuário deve ser válida

  Cenário: Validar criação de usuário com e-mail inválido
    Dado que possuo acesso à API de autenticação
    Quando envio criação de usuário com e-mail inválido
    Então a resposta de criação de usuário deve ser válida

