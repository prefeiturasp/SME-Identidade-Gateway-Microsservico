# EOL Autenticação

## Objetivo

Disponibilizar a recuperação de senha com o contrato da API EOL legada, utilizando o **MS-Token** para gerenciar as solicitações e enviar o e-mail, e o **Keycloak** para manter a credencial e o histórico de senhas.

## Endpoint `POST /identidade-gateway/api/v1/eol-autenticacao/RecuperarSenha/usuario`

```http
POST /identidade-gateway/api/v1/eol-autenticacao/RecuperarSenha/usuario?sistema=1 HTTP/1.1
X-API-Key: <chave-do-gateway>
Content-Type: application/json

"1234567"
```

O parâmetro `sistema` identifica o sistema para o qual a senha será recuperada. A busca considera o login cadastrado no Keycloak, sem utilizar e-mail ou atributos adicionais como alternativas.

A rota é protegida pela API Key padrão do Gateway (`API_KEY`, no cabeçalho definido por `API_KEY_HEADER`). A adaptação do caminho público legado e da chave `x-api-eol-key` fica a cargo do proxy.

## Fluxo

1. O Gateway valida a requisição e consulta o usuário no Keycloak pelo username exato, sem diferenciar maiúsculas de minúsculas.
2. O Gateway envia o login, o código do sistema, o contexto e os dados normalizados da conta ao MS-Token.
3. O MS-Token valida o sistema e o e-mail, gera um UUID e substitui a solicitação anterior da mesma conta.
4. O MS-Token envia o modelo HTML do legado com nome, login e link para a página de recuperação do sistema.
5. O Gateway retorna o endereço de e-mail de destino como string JSON.

Falhas de comunicação ou de envio do e-mail são retornadas como erros, preservando a distinção entre falha técnica e usuário não encontrado.

## Regras de recuperação

- O código de recuperação tem validade de seis horas.
- Uma nova solicitação substitui a anterior da mesma conta, inclusive quando feita para outro sistema.
- O link utiliza a página de recuperação cadastrada para o sistema, seguida do UUID.
- A consulta de validade não consome o código.
- Após a troca bem-sucedida, o código não pode ser utilizado novamente.

## Respostas

| HTTP | Comportamento |
| --- | --- |
| `200 OK` | E-mail enviado; retorna o endereço de destino como string JSON. |
| `400 Bad Request` | Login ausente, usuário não encontrado, sistema inválido ou não cadastrado, ou e-mail ausente ou inválido. |
| `401 Unauthorized` | API Key do Gateway ausente ou inválida. |
| `502 Bad Gateway` | Falha no envio de e-mail ou na comunicação com os serviços necessários. |
| `504 Gateway Timeout` | Tempo de espera excedido na chamada ao MS-Token. |

### Exemplo de solicitação concluída:

```json
"usuario@exemplo.com"
```

Exemplo de usuário não encontrado (`400`):

```json
"Usuário ou RF não encontrado"
```

## Endpoint `POST /identidade-gateway/api/v1/eol-autenticacao/RecuperarSenha/token/validar`

```http
POST /identidade-gateway/api/v1/eol-autenticacao/RecuperarSenha/token/validar HTTP/1.1
X-API-Key: <chave-do-gateway>
Content-Type: application/json

"eab64661-dc5d-4e09-92d5-1b629ab31530"
```

A rota usa a mesma API Key do Gateway e informa se o código recebido no link ainda pode ser utilizado. A consulta não consome o código e pode ser repetida antes da troca de senha.

A resposta de sucesso é um booleano JSON, sem objeto envolvente.
Essa consulta utiliza somente o MS-Token e não acessa o Keycloak.

| Situação | Resposta |
| --- | --- |
| Código válido e dentro do prazo | `200 true` |
| UUID inexistente, expirado, substituído, reservado para alteração ou já utilizado | `200 false` |
| Corpo que não seja uma string JSON contendo um UUID | `400`, com mensagem de código inválido |
| API Key ausente ou inválida | `401` |
| Falha na consulta ao MS-Token | `502` |
| Tempo de espera excedido na chamada ao MS-Token | `504` |

Uma falha de consulta não é convertida em `false`: esse valor representa uma consulta concluída em que o código não está disponível para uso.

## Endpoint `POST /identidade-gateway/api/v1/eol-autenticacao/AlterarSenha`

```http
POST /identidade-gateway/api/v1/eol-autenticacao/AlterarSenha HTTP/1.1
X-API-Key: <chave-do-gateway>
Content-Type: application/x-www-form-urlencoded

Token=eab64661-dc5d-4e09-92d5-1b629ab31530&Senha=NovaSenha123
```

`Token` identifica a solicitação de recuperação e `Senha` informa a nova credencial. A rota exige a mesma API Key do Gateway e aceita formulário URL encoded ou multipart. Os nomes dos campos não diferenciam maiúsculas de minúsculas.

A variante com barra final, `/identidade-gateway/api/v1/eol-autenticacao/AlterarSenha/`, também é aceita.

O Gateway obtém no MS-Token a identidade vinculada ao código e consulta a conta atual no Keycloak. O MS-Token verifica o prazo, a conta habilitada e as regras de senha, e reserva o uso do código. Somente após essa autorização o Gateway altera a senha no Keycloak e confirma o resultado ao MS-Token. Após sucesso, o código é invalidado e o login é retornado como string JSON.

### Regras da senha

- De 8 a 12 caracteres, sem espaços.
- Pelo menos uma letra maiúscula, uma minúscula e um número ou caractere especial aceito pelo legado (`!@#$-%&/\[]|*()_=+`).
- Senhas padrão de SGP e Plateia são rejeitadas.
- As últimas cinco senhas são rejeitadas pelo histórico do Keycloak.

Uma rejeição pelas regras de senha permite nova tentativa com o mesmo código enquanto ele estiver válido. Se houver falha de comunicação durante a troca e o resultado for incerto, uma nova solicitação de recuperação pode ser necessária.

A reserva impede duas alterações com o mesmo código. Se a confirmação do resultado for perdida, ele permanece bloqueado. A conclusão de uma operação anterior não invalida um link solicitado depois dela.

### Respostas da alteração

| HTTP | Comportamento |
| --- | --- |
| `200 OK` | Senha alterada e código invalidado; retorna o login como string JSON. |
| `400 Bad Request` | Formulário inválido ou campos obrigatórios ausentes. |
| `401 Unauthorized` | API Key ausente ou inválida, código inválido ou expirado, conta indisponível, senha fora do padrão, senha padrão ou presente no histórico. |
| `415 Unsupported Media Type` | Corpo enviado em formato diferente dos formulários aceitos. |
| `502 Bad Gateway` | Falha na comunicação com os serviços ou histórico de senhas não configurado no Keycloak. |
| `504 Gateway Timeout` | Tempo de espera excedido na chamada ao MS-Token. |

Exemplo de alteração concluída:

```json
"1234567"
```

As mensagens de negócio são retornadas como strings JSON. Erros de campos obrigatórios usam um objeto com os nomes dos campos e suas mensagens. Os erros de autenticação seguem o formato padrão do Gateway.

Os endpoints de solicitação e validação também aceitam `application/json-patch+json`, utilizado pelo cliente .NET do SGP.

## Integração de identidade

As consultas ao usuário, a verificação do histórico e a alteração da credencial ficam no Gateway. O MS-Token mantém as solicitações, as regras de senha, as reservas e o envio do e-mail; recebe somente dados normalizados e resultados de operações autenticadas.

O adaptador `apps.provedores.keycloak.ProvedorKeycloak` usa a conexão administrativa já configurada no Gateway. `PROVEDOR_IDENTIDADE` seleciona a implementação e tem essa classe como padrão. Para a recuperação, a busca considera somente o login exato.

O realm precisa ter `passwordHistory(5)` ou superior. O histórico considerado é o existente no Keycloak; senhas anteriores que não foram migradas não participam dessa verificação. Ao preparar a troca, o adaptador remove apenas a ação `UPDATE_PASSWORD`, preservando as demais ações pendentes da conta.
