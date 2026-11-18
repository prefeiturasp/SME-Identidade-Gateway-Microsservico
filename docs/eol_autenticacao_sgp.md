# EOL Autenticação SGP

## Objetivo

Disponibilizar temporariamente o contrato de consulta de dados da API EOL legada, usando o MS-ETL e o MS-Abrangência, sem conexão direta do Gateway com o CoreSSO.

## Endpoint

```http
GET /identidade-gateway/api/v1/eol-autenticacao-sgp/{login}/dados/ HTTP/1.1
X-API-Key: <chave-do-gateway>

```

O parâmetro `login` é obrigatório. A autenticação utiliza a API Key padrão do Gateway, sem validação da chave legada.

## Fluxo

1. Consultar o MS-ETL pelo login: `GET /identidade-etl/api/v1/etl/coresso/usuarios/{login}/dados/`.
2. Se o ETL responder `200`, compor o DTO com os dados cadastrais; não consultar a Abrangência.
3. Se o ETL responder `204`, consultar a DRE vigente: `GET /api/abrangencia/usuarios/{login}/dre-vigente`.
4. Se a Abrangência responder `200`, retornar apenas `dreCodigo` preenchido e `emailValido` como `false`.
5. Se ambas as consultas retornarem `204`, responder `204 No Content`, sem corpo.

Erros de integração não são tratados como ausência de dados.

## Regras de composição

- `cpf` e `nome`: dados obtidos do CoreSSO via ETL.
- `codigoRf`: login original quando compatível com `int.TryParse` do Legado (`Int32`); caso contrário, `null`.
- `email`: preservado apenas se válido; caso contrário, `null`.
- `emailValido`: resultado booleano da validação do e-mail.
- `dreCodigo`: preenchido somente no fluxo alternativo da Abrangência.

## Respostas

| HTTP | Comportamento |
| --- | --- |
| `200 OK` | Retorna o DTO de seis campos, com dados cadastrais ou apenas a DRE vigente. |
| `204 No Content` | Não há usuário no CoreSSO nem DRE vigente; sem corpo. |
| `400 Bad Request` | Erro na consulta ao CoreSSO ou falha inesperada de integração, conforme as mensagens do contrato legado. |
| `401 Unauthorized` | API Key do Gateway ausente ou inválida. |

Exemplo com dados do CoreSSO:

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
