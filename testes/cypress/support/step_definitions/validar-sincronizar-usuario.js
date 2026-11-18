import { When, Then } from "cypress-cucumber-preprocessor/steps";

When('consulto o endpoint de sincronização de usuário', () => {
  cy.chamarEndpointSwagger('sincronizarUsuario').as("response");
});

Then('a resposta de sincronização de usuário deve ser válida', () => {
  const expected = "400".split(",").map(Number);
  cy.get("@response").then((response) => {
    expect(expected, "status recebido: " + response.status).to.include(response.status);
  });
});
