import { When, Then } from "cypress-cucumber-preprocessor/steps";

When('consulto o endpoint de validação de token de cliente', () => {
  cy.chamarEndpointSwagger('validarTokenCliente').as("response");
});

Then('a resposta de validação de token de cliente deve ser válida', () => {
  const expected = "400".split(",").map(Number);
  cy.get("@response").then((response) => {
    expect(expected, "status recebido: " + response.status).to.include(response.status);
  });
});
