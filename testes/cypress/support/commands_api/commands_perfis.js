Cypress.Commands.add("getPerfisPorLogin", () => {
  return cy.request({
    method: "GET",
    url: `${Cypress.env("API_URL")}/autenticacao/usuarios/${Cypress.env("USUARIO_LOGIN")}/perfis/`,
    headers: {
      accept: "application/json",
      [Cypress.env("API_KEY_HEADER")]: Cypress.env("API_KEY"),
    },
    failOnStatusCode: false,
  });
});

Cypress.Commands.add("getDadosAcesso", () => {
  return cy.request({
    method: "GET",
    url: `${Cypress.env("API_URL")}/autenticacao/usuarios/${Cypress.env("USUARIO_LOGIN")}/perfis/${Cypress.env("USUARIO_PERFIL")}/acesso/`,
    headers: {
      accept: "application/json",
      [Cypress.env("API_KEY_HEADER")]: Cypress.env("API_KEY"),
    },
    failOnStatusCode: false,
  });
});
