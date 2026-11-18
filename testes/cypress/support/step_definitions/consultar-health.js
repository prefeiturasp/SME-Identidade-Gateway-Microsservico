import { When, Then } from "cypress-cucumber-preprocessor/steps";

When('consulto o endpoint de health check', () => {
  cy.chamarEndpointSwagger('health').as("response");
});

Then('a resposta de health check deve ser válida', () => {
  const expected = "200".split(",").map(Number);
  cy.get("@response").then((response) => {
    expect(expected, "status recebido: " + response.status).to.include(response.status);
  });
});
