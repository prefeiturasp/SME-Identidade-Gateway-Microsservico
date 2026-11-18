# language: pt

Funcionalidade: API - Alteração de senha

  Cenário: Validar endpoint alteração de senha
    Quando consulto o endpoint de alteração de senha
    Então a resposta de alteração de senha deve ser válida

  Cenário: Validar endpoint alteração de senha sem enviar dados
    Quando consulto o endpoint de alteração de senha sem enviar dados
    Então a resposta de alteração de senha deve ser válida

  Cenário: Validar alteração de senha vazia
    Quando envio solicitação de alteração de senha com senha vazia
    Então a resposta de alteração de senha deve ser válida

