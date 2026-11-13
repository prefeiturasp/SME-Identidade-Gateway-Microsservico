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

  if (options.omitirLogin) {
    delete body.login;
  }

  const headers = {
    accept: "application/json",
    "Content-Type": "application/json",
  };

  if (!options.omitirApiKey) {
    headers[Cypress.env("API_KEY_HEADER")] =
      options.apiKey !== undefined ? options.apiKey : Cypress.env("API_KEY");
  }

  return cy.request({
    method: "POST",
    url: `${Cypress.env("API_URL")}/autenticacao/login/`,
    headers,
    body,
    failOnStatusCode: false,
  });
});

Cypress.Commands.add("postLogout", (refreshToken, options = {}) => {
  const body = {};

  if (refreshToken !== undefined) {
    body.refresh_token = refreshToken;
  }

  const headers = {
    accept: "application/json",
    "Content-Type": "application/json",
  };

  if (!options.omitirApiKey) {
    headers[Cypress.env("API_KEY_HEADER")] =
      options.apiKey !== undefined ? options.apiKey : Cypress.env("API_KEY");
  }

  return cy.request({
    method: "POST",
    url: `${Cypress.env("API_URL")}/autenticacao/logout/`,
    headers,
    body,
    failOnStatusCode: false,
  });
});

Cypress.Commands.add("postValidarToken", (token, options = {}) => {
  const body = {};

  if (token !== undefined) {
    body.token = token;
  }

  const headers = {
    accept: "application/json",
    "Content-Type": "application/json",
  };

  if (!options.omitirApiKey) {
    headers[Cypress.env("API_KEY_HEADER")] =
      options.apiKey !== undefined ? options.apiKey : Cypress.env("API_KEY");
  }

  return cy.request({
    method: "POST",
    url: `${Cypress.env("API_URL")}/autenticacao/validar-token/`,
    headers,
    body,
    failOnStatusCode: false,
  });
});
