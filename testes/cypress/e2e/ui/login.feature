# language: pt

@admin-ui
Funcionalidade: Tela de login do painel administrativo

  Contexto:
    Dado que estou na tela de login do painel administrativo

  Cenário: Exibir os campos de acesso
    Então os campos de usuário e senha devem estar visíveis
    E o botão Entrar deve estar desabilitado

  Cenário: Habilitar o acesso ao preencher as credenciais
    Quando preencho as credenciais cadastradas
    Então o botão Entrar deve estar habilitado

  Cenário: Mostrar e ocultar a senha
    Quando preencho a senha cadastrada
    E alterno a exibição da senha
    Então a senha deve ficar visível
    Quando alterno a exibição da senha
    Então a senha deve ficar oculta

  @requires-auth
  Cenário: Entrar no painel com credenciais válidas
    Quando preencho as credenciais cadastradas
    E envio o formulário de login
    Então devo sair da tela de login
