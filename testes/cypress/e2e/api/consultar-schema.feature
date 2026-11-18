# language: pt

Funcionalidade: API - Schema da API

  Cenário: Validar endpoint schema da API
    Quando consulto o endpoint de schema da API
    Então a resposta de schema da API deve ser válida

  Cenário: Validar que o schema documenta alteração de e-mail
    Quando consulto o endpoint de schema da API
    Então o schema deve documentar o endpoint de alteração de e-mail

