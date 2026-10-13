# language: pt

Funcionalidade: API - Autenticação

  Cenário: Validar login com senha inválida
    Dado que possuo acesso à API de autenticação
    Quando realizo login com senha inválida
    Então retorna o status 401

  Cenário: Validar login sem informar a senha
    Dado que possuo acesso à API de autenticação
    Quando realizo login sem informar a senha
    Então retorna o status 400

  Cenário: Validar login sem a API Key
    Dado que possuo acesso à API de autenticação
    Quando realizo login sem informar a API Key
    Então retorna o status 401

  Cenário: Validar logout sem informar o refresh token
    Dado que possuo acesso à API de autenticação
    Quando realizo logout sem informar o refresh token
    Então retorna o status 400
