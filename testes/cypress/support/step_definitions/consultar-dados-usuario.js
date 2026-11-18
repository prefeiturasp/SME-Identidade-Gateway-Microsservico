import { When, Then } from "cypress-cucumber-preprocessor/steps";

When("consulto endpoint de consulta de dados do usuário sem API Key", () => {
  cy.chamarEndpointSwagger("dadosUsuario", { omitirApiKey: true }).as("response");
});

Then("endpoint de consulta de dados do usuário rejeita requisicao sem API Key", () => {
  cy.get("@response").then((response) => expect(response.status).to.eq(401));
});