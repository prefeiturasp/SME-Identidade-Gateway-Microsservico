Cypress.Commands.add("getDadosUsuario", () => {
  return cy.request({
    method: "GET",
    url: `${Cypress.env("API_URL")}/autenticacao/usuarios/${Cypress.env("USUARIO_LOGIN")}/dados/`,
    headers: {
      accept: "application/json",
      [Cypress.env("API_KEY_HEADER")]: Cypress.env("API_KEY"),
    },
    failOnStatusCode: false,
  });
});
