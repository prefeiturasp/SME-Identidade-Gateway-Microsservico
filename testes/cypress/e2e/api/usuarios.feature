# language: pt

Funcionalidade: API - Usuários

  Cenário: Validar consulta de dados do usuário
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de dados do usuário
    Então retorna o status 200
    E o retorno deve conter os dados cadastrais do usuário
