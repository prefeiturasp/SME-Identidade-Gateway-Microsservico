# language: pt

Funcionalidade: API - Alteração de e-mail

  Cenário: Validar endpoint alteração de e-mail
    Quando consulto o endpoint de alteração de e-mail
    Então a resposta de alteração de e-mail deve ser válida

  Cenário: Validar endpoint alteração de e-mail sem enviar dados
    Quando consulto o endpoint de alteração de e-mail sem enviar dados
    Então a resposta de alteração de e-mail deve ser válida

  Cenário: Validar alteração de e-mail com formato inválido
    Quando envio solicitação de alteração de e-mail com e-mail inválido
    Então a resposta de alteração de e-mail deve ser válida

