# language: pt

Funcionalidade: API - Health check

  Cenário: Validar endpoint health check
    Quando consulto o endpoint de health check
    Então a resposta de health check deve ser válida

  Cenário: Validar estrutura da resposta de health check
    Quando consulto o endpoint de health check
    Então a resposta de health check deve informar o estado da aplicação e dependências

