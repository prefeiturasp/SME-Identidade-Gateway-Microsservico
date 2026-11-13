Cypress.Commands.add("getDadosUsuario", (options = {}) => {
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
    url: `${Cypress.env("API_URL")}/autenticacao/usuarios/${login}/dados/`,
    headers,
    failOnStatusCode: false,
  });
});
