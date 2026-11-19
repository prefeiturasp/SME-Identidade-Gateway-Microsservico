# language: pt

Funcionalidade: Painel de controle

  Cenário: Visualizar o painel após autenticação
    Dado que estou na tela de login do painel administrativo
    Quando preencho as credenciais cadastradas
    E envio o formulário de login
    Então devo sair da tela de login
    E os principais elementos do painel devem estar visíveis
