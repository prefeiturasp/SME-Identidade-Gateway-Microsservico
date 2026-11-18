# language: pt

Funcionalidade: API - Validar logout

  Cenário: Validar endpoint de logout
    Quando consulto endpoint de logout
    Então endpoint de logout responde conforme esperado

  Cenário: Validar endpoint de notificacao de logout
    Quando consulto endpoint de notificacao de logout
    Então endpoint de notificacao de logout responde conforme esperado

Cenário: Validar logout sem informar o refresh token
    Dado que possuo acesso à API de autenticação
    Quando realizo logout sem informar o refresh token
    Então retorna o status 400

Cenário: Validar logout com refresh token vazio
    Dado que possuo acesso à API de autenticação
    Quando realizo logout com refresh token vazio
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

@ignore
  Cenário: Validar logout com o refresh token obtido no login
    Dado que possuo acesso à API de autenticação
    Quando realizo logout com o refresh token obtido no login
    Então retorna o status 200
    E o retorno deve confirmar o encerramento da sessão
