# language: pt

Funcionalidade: API - Autenticação

  Cenário: Validar login com credenciais válidas
    Dado que possuo acesso à API de autenticação
    Quando realizo login com credenciais válidas
    Então retorna o status 200
    E o retorno deve conter os dados da sessão do usuário

  Cenário: Validar login com senha inválida
    Dado que possuo acesso à API de autenticação
    Quando realizo login com senha inválida
    Então retorna o status 401

  Cenário: Validar login sem informar a senha
    Dado que possuo acesso à API de autenticação
    Quando realizo login sem informar a senha
    Então retorna o status 400

  Cenário: Validar login sem informar o login
    Dado que possuo acesso à API de autenticação
    Quando realizo login sem informar o login
    Então retorna o status 400

  Cenário: Validar login sem a API Key
    Dado que possuo acesso à API de autenticação
    Quando realizo login sem informar a API Key
    Então retorna o status 401

  Cenário: Validar login com API Key inválida
    Dado que possuo acesso à API de autenticação
    Quando realizo login com API Key inválida
    Então retorna o status 401

  Cenário: Validar logout sem informar o refresh token
    Dado que possuo acesso à API de autenticação
    Quando realizo logout sem informar o refresh token
    Então retorna o status 400

  Cenário: Validar logout sem a API Key
    Dado que possuo acesso à API de autenticação
    Quando realizo logout sem informar a API Key
    Então retorna o status 401

  Cenário: Validar logout com refresh token inválido
    Dado que possuo acesso à API de autenticação
    Quando realizo logout com refresh token inválido
    Então retorna o status 200
    E o retorno deve confirmar o encerramento da sessão

  Cenário: Validar logout com o refresh token obtido no login
    Dado que possuo acesso à API de autenticação
    Quando realizo logout com o refresh token obtido no login
    Então retorna o status 200
    E o retorno deve confirmar o encerramento da sessão

  Cenário: Validar token enriquecido sem informar o token
    Dado que possuo acesso à API de autenticação
    Quando valido o token enriquecido sem informar o token
    Então retorna o status 400

  Cenário: Validar token enriquecido sem a API Key
    Dado que possuo acesso à API de autenticação
    Quando valido o token enriquecido sem informar a API Key
    Então retorna o status 401
