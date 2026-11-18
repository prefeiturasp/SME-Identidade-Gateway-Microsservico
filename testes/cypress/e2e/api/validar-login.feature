# language: pt

Funcionalidade: API - Validar login

  Cenário: Validar endpoint de login de usuario
    Quando consulto endpoint de login de usuario
    Então endpoint de login de usuario responde conforme esperado

  Cenário: Validar endpoint de login de cliente
    Quando consulto endpoint de login de cliente
    Então endpoint de login de cliente responde conforme esperado

@ignore
  Cenário: Validar login com credenciais válidas
    Dado que possuo acesso à API de autenticação
    Quando realizo login com credenciais válidas
    Então retorna o status 200
    E o retorno deve conter os dados da sessão do usuário

@ignore
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

Cenário: Validar login com senha vazia
    Dado que possuo acesso à API de autenticação
    Quando realizo login com senha vazia
    Então retorna o status 400

Cenário: Validar login com login vazio
    Dado que possuo acesso à API de autenticação
    Quando realizo login com login vazio
    Então retorna o status 400

Cenário: Validar login com valor nulo
    Dado que possuo acesso à API de autenticação
    Quando realizo login com login nulo
    Então retorna o status 400

Cenário: Validar login sem a API Key
    Dado que possuo acesso à API de autenticação
    Quando realizo login sem informar a API Key
    Então retorna o status 401

Cenário: Validar login com API Key inválida
    Dado que possuo acesso à API de autenticação
    Quando realizo login com API Key inválida
    Então retorna o status 401
