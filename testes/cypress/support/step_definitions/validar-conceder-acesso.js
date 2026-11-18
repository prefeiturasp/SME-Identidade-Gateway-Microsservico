import { When, Then } from "cypress-cucumber-preprocessor/steps";

When('consulto o endpoint de concessão de acesso', () => {
  cy.chamarEndpointSwagger('concederAcesso').as("response");
});

When('envio concessão de acesso sem roles', () => {
  cy.chamarEndpointSwagger('concederAcessoRolesVazias').as("response");
});

Then('a resposta de concessão de acesso deve ser válida', () => {
  const expected = "400".split(",").map(Number);
  cy.get("@response").then((response) => {
    expect(expected, "status recebido: " + response.status).to.include(response.status);
  });
});
