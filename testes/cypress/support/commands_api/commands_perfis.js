Cypress.Commands.add("getPerfisPorLogin", (options = {}) => {
  const login =
    options.login !== undefined ? options.login : Cypress.env("USUARIO_LOGIN");

  const headers = {
    accept: "application/json",
  };

  if (!options.omitirApiKey) {
    headers[Cypress.env("API_KEY_HEADER")] =
      options.apiKey !== undefined ? options.apiKey : Cypress.env("API_KEY");
  }

  return cy.request({
    method: "GET",
    url: `${Cypress.env("API_URL")}/autenticacao/usuarios/${login}/perfis/`,
    headers,
    failOnStatusCode: false,
  });
});

Cypress.Commands.add("getDadosAcesso", (options = {}) => {
  const login =
    options.login !== undefined ? options.login : Cypress.env("USUARIO_LOGIN");
  const perfil =
    options.perfil !== undefined
      ? options.perfil
      : Cypress.env("USUARIO_PERFIL");

  const headers = {
    accept: "application/json",
  };

  if (!options.omitirApiKey) {
    headers[Cypress.env("API_KEY_HEADER")] =
      options.apiKey !== undefined ? options.apiKey : Cypress.env("API_KEY");
  }

  return cy.request({
    method: "GET",
    url: `${Cypress.env("API_URL")}/autenticacao/usuarios/${login}/perfis/${perfil}/acesso/`,
    headers,
    failOnStatusCode: false,
  });
});
