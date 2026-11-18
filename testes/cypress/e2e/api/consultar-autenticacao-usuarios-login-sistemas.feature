# language: pt

Funcionalidade: API - Sistemas

  @ignore
  Cenário: Validar consulta de sistemas do usuário
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de sistemas do usuário
    Então retorna o status 200
    E o retorno deve conter a lista de sistemas

  @ignore
  Cenário: Validar estrutura dos sistemas do usuário
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de sistemas do usuário
    Então retorna o status 200
    E os sistemas do usuário devem ter estrutura válida

  Cenário: Validar consulta de sistemas do usuário sem a API Key
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de sistemas do usuário sem informar a API Key
    Então retorna o status 401

  Cenário: Validar consulta de sistemas do usuário com API Key inválida
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de sistemas do usuário com API Key inválida
    Então retorna o status 401

  Cenário: Validar que o endpoint de consulta de sistemas exige API Key
    Quando consulto endpoint de consulta de sistemas sem API Key
    Então endpoint de consulta de sistemas rejeita requisicao sem API Key