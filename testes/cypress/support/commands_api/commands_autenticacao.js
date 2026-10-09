Cypress.Commands.add("postLogin", (options = {}) => {
  const body = {
    login:
      options.login !== undefined
        ? options.login
        : `${Cypress.env("USUARIO_LOGIN")}`,
    senha:
      options.senha !== undefined
        ? options.senha
        : `${Cypress.env("USUARIO_SENHA")}`,
  };

  if (options.omitirSenha) {
    delete body.senha;
  }

  return cy.request({
    method: "POST",
    url: `${Cypress.env("API_URL")}/autenticacao/login/`,
    headers: {
      accept: "application/json",
      "Content-Type": "application/json",
      ...(options.omitirApiKey
        ? {}
        : { [Cypress.env("API_KEY_HEADER")]: Cypress.env("API_KEY") }),
    },
    body,
    failOnStatusCode: false,
  });
});

Cypress.Commands.add("postLogout", (refreshToken) => {
  const body = {};

  if (refreshToken !== undefined) {
    body.refresh_token = refreshToken;
  }

  return cy.request({
    method: "POST",
    url: `${Cypress.env("API_URL")}/autenticacao/logout/`,
    headers: {
      accept: "application/json",
      "Content-Type": "application/json",
      [Cypress.env("API_KEY_HEADER")]: Cypress.env("API_KEY"),
    },
    body,
    failOnStatusCode: false,
  });
});
