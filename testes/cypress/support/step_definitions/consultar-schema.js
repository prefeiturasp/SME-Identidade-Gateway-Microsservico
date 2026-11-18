import { When, Then } from "cypress-cucumber-preprocessor/steps";

When('consulto o endpoint de schema da API', () => {
  cy.chamarEndpointSwagger('schema').as("response");
});

Then('a resposta de schema da API deve ser válida', () => {
  const expected = "200".split(",").map(Number);
  cy.get("@response").then((response) => {
    expect(expected, "status recebido: " + response.status).to.include(response.status);
  });
});
