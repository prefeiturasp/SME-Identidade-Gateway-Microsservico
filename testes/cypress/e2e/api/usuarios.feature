# language: pt

Funcionalidade: API - Usuários

  Cenário: Validar consulta de dados do usuário
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de dados do usuário
    Então retorna o status 200
    E o retorno deve conter os dados cadastrais do usuário

  Cenário: Validar consulta de dados do usuário com o CPF e o nome cadastrados
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de dados do usuário
    Então retorna o status 200
    E o retorno deve conter o CPF e o nome cadastrados do usuário

  Cenário: Validar consulta de dados do usuário sem a API Key
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de dados do usuário sem informar a API Key
    Então retorna o status 401

  Cenário: Validar consulta de dados do usuário com API Key inválida
    Dado que possuo acesso à API de autenticação
    Quando realizo consulta de dados do usuário com API Key inválida
    Então retorna o status 401
