# SME Identidade Gateway Microsserviço

Documentação técnica do serviço responsável pela centralização das capacidades de autenticação, validação de identidade e propagação segura de contexto autenticado para aplicações e microsserviços da plataforma SME.

O microsserviço atua como camada transversal de autenticação e integração com provedores de identidade corporativos, garantindo padronização de acesso, rastreabilidade e segurança operacional.

Sua função é validar identidades, processar credenciais, propagar contexto autenticado entre serviços e apoiar a aplicação consistente de políticas de segurança em toda a plataforma. Também expõe a gestão de usuário (criação, sincronização e concessão de acesso), delegando a lógica de provisionamento ao SME-Identidade-ETL.

```{toctree}
:maxdepth: 2
:caption: Conteúdo

autenticacao
gestao_usuario
api
```