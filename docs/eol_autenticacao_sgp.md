# Compatibilidade de autenticação com o SGP

## Verificar e-mail associado a outro usuário

`GET /identidade-gateway/api/v1/eol-autenticacao-sgp/{login}/ValidarEmailExistente/{email}`

A rota usa o prefixo configurado para o app SGP e não possui barra final.
O gateway exige sua API Key habitual (`API_KEY`, no header definido por
`API_KEY_HEADER`). A adaptação do caminho público legado e da chave
`x-api-eol-key` fica a cargo do proxy.

`login` informa o RF ou CPF do usuário a excluir da busca; `email` deve ser um
endereço válido e completo. O gateway remove espaços externos e consulta o
Keycloak, preservando a caixa do e-mail. A resolução do login reutiliza a busca
existente por username, RF, CPF ou e-mail.

A verificação considera todas as contas do realm configurado, inclusive
inativas e com e-mail não verificado. A conta identificada pelo login é excluída
por seu ID, independentemente do username cadastrado.

A resposta de sucesso é um booleano JSON, sem objeto envolvente.

| Situação | Resposta |
|---|---|
| E-mail livre ou associado somente à própria conta | `200 false` |
| E-mail associado a qualquer outra conta | `200 true` |
| Parâmetros inválidos | `400`, com erros por campo |
| API Key ausente ou inválida | `401` |
| Login não encontrado no Keycloak | `404`, com campo `erro` |
| Falha na consulta ao Keycloak | `502`, com erro genérico |

Uma falha de consulta não é convertida em `false`: esse valor representa uma
consulta concluída sem outra conta associada ao e-mail.

## Organização interna

A view valida a entrada e chama `existe_email_em_outro_usuario`, no módulo
`apps.autenticacao.services`, passando uma instância de `ConsultaUsuariosKeycloak`.
O serviço depende apenas do protocolo `ConsultaUsuarios`, sem importar Django,
DRF ou o SDK do Keycloak.

O adaptador fica em `apps.autenticacao.keycloak_admin`, compartilha um cliente
administrativo criado sob demanda por consulta e traduz exceções do SDK para
`ConsultaUsuariosIndisponivelError`. A view converte essa falha em `502` e
`UsuarioNaoEncontradoError` em `404`, sem expor detalhes internos da integração.

A busca por e-mail usa `email` e `exact=True`. A implementação de `get_users`
percorre todas as páginas quando não recebe `first` ou `max`; o adaptador
preserva esse comportamento. Este endpoint não chama o ETL nem acessa o CoreSSO.

## Limitação do consumidor legado

O consumidor SGP atual converte respostas HTTP de erro em `false`. Isso pode
interpretar uma falha de consulta como ausência de outra conta. O gateway
distingue a indisponibilidade do provedor da ausência de outra conta; o ajuste
do consumidor e a configuração do proxy não fazem parte desta implementação.
