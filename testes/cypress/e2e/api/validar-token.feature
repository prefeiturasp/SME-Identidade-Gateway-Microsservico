# language: pt

Funcionalidade: API - Validar token

  Cenário: Validar endpoint de token
    Quando consulto endpoint de validacao de token
    Então endpoint de validacao de token responde conforme esperado

Cenário: Validar token enriquecido sem informar o token
    Dado que possuo acesso à API de autenticação
    Quando valido o token enriquecido sem informar o token
    Então retorna o status 400

Cenário: Validar token enriquecido vazio
    Dado que possuo acesso à API de autenticação
    Quando valido o token enriquecido vazio
    Então retorna o status 400

Cenário: Validar token enriquecido contendo apenas espaços
    Dado que possuo acesso à API de autenticação
    Quando valido o token enriquecido contendo apenas espaços
    Então retorna o status 400

Cenário: Validar token enriquecido sem a API Key
    Dado que possuo acesso à API de autenticação
    Quando valido o token enriquecido sem informar a API Key
    Então retorna o status 401
