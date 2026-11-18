import { When, Then } from "cypress-cucumber-preprocessor/steps";

When('consulto o endpoint de alteração de senha', () => {
  cy.chamarEndpointSwagger('alterarSenha').as("response");
});

Then('a resposta de alteração de senha deve ser válida', () => {
  const expected = "400".split(",").map(Number);
  cy.get("@response").then((response) => {
    expect(expected, "status recebido: " + response.status).to.include(response.status);
  });
});
