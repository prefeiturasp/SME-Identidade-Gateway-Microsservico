# language: pt

Funcionalidade: API - Sistemas

  Cenário: Validar consulta de sistemas do usuário
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de sistemas do usuário
    Então retorna o status 200
    E o retorno deve conter a lista de sistemas
