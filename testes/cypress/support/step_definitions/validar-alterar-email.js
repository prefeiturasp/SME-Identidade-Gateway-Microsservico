import { When, Then } from "cypress-cucumber-preprocessor/steps";

When('consulto o endpoint de alteração de e-mail', () => {
  cy.chamarEndpointSwagger('alterarEmail').as("response");
});

When('consulto o endpoint de alteração de e-mail sem enviar dados', () => {
  cy.chamarEndpointSwagger('alterarEmail').as("response");
});

When('envio solicitação de alteração de e-mail com e-mail inválido', () => {
  cy.chamarEndpointSwagger('alterarEmailInvalido').as("response");
});

Then('a resposta de alteração de e-mail deve ser válida', () => {
  const expected = "400".split(",").map(Number);
  cy.get("@response").then((response) => {
    expect(expected, "status recebido: " + response.status).to.include(response.status);
  });
});
