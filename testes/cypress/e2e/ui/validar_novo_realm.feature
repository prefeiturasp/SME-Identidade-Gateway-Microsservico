# language: pt

Funcionalidade: Formulário de novo realm

  Cenário: Exibir campos e opções do novo realm
    Dado que estou na tela de login do painel administrativo
    Quando preencho as credenciais cadastradas
    E envio o formulário de login
    Então devo sair da tela de login
    Quando abro o formulário de novo realm
    Então os campos e opções do novo realm devem estar visíveis
