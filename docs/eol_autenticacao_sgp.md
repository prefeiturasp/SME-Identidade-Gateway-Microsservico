# EOL Autenticação SGP

## Objetivo

Disponibilizar temporariamente a consulta de dados de usuário com o contrato da API EOL legada, utilizando o **Keycloak** como fonte cadastral e o **MS-Abrangência** para a consulta alternativa da DRE vigente.

## Endpoint `GET /identidade-gateway/api/v1/eol-autenticacao-sgp/{login}/dados/`

```http
GET /identidade-gateway/api/v1/eol-autenticacao-sgp/{login}/dados/ HTTP/1.1
X-API-Key: <chave-do-gateway>

```

O parâmetro `login` identifica o usuário consultado. A rota é protegida pela API Key padrão do Gateway, sem exigir a chave legada.

## Fluxo

1. Consultar o usuário no Keycloak usando `keycloak_admin.obter_dados_usuario(login)`.
2. Se o usuário existir e `ativo` for `True`, compor o retorno cadastral, sem consultar a Abrangência.
3. Se o usuário estiver inativo ou não for encontrado, consultar `GET /api/abrangencia/usuarios/{login}/dre-vigente`.
4. Se houver DRE vigente, retornar somente `dreCodigo` preenchido entre os campos cadastrais.
5. Se não houver usuário elegível nem DRE vigente, retornar `204 No Content` sem corpo.

Falhas técnicas do Keycloak ou do MS-Abrangência **não** são interpretadas como usuário inexistente.

## Regras de composição

- `cpf`: atributo `cpf` do usuário no Keycloak.
- `nome`: nome disponibilizado pelo Keycloak.
- `codigoRf`: login original, quando compatível com `int.TryParse` (`Int32`) do Legado; caso contrário, `null`.
- `email`: e-mail do Keycloak, retornado somente quando válido; caso contrário, `null`.
- `emailValido`: resultado booleano da validação do e-mail.
- `dreCodigo`: `null` quando há usuário ativo; preenchido apenas na consulta alternativa ao MS-Abrangência.

Um usuário encontrado, ativo e com algum campo cadastral vazio continua no fluxo de dados cadastrais, sem consultar a DRE.

## Respostas

| HTTP | Comportamento |
| --- | --- |
| `200 OK` | Usuário ativo encontrado no Keycloak: retorna dados cadastrais; ou DRE vigente encontrada na consulta alternativa. |
| `204 No Content` | Usuário inexistente ou inativo no Keycloak e sem DRE vigente; resposta sem corpo. |
| `400 Bad Request` | Falha técnica na consulta ao Keycloak ou ao MS-Abrangência; mensagem genérica do contrato de compatibilidade. |
| `401 Unauthorized` | API Key do Gateway ausente ou inválida. |

### Exemplo usuário ativo no Keycloak:

```json
{
  "cpf": "00123456789",
  "nome": "USUARIO TESTE",
  "codigoRf": "7210418",
  "email": "usuario@exemplo.com",
  "dreCodigo": null,
  "emailValido": true
}
```

Exemplo com apenas a DRE vigente:

```json
{
  "cpf": null,
  "nome": null,
  "codigoRf": null,
  "email": null,
  "dreCodigo": "108600",
  "emailValido": false
}
```

O aplicativo `eol_autenticacao_sgp` é uma camada de compatibilidade temporária e poderá ser removido após a migração dos consumidores.

## Endpoint `GET /identidade-gateway/api/v1/eol-autenticacao-sgp/{login}/ValidarEmailExistente/{email}`

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
