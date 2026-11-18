import { When, Then } from "cypress-cucumber-preprocessor/steps";

When("consulto endpoint de consulta de acesso do perfil sem API Key", () => {
  cy.chamarEndpointSwagger("acessoPerfil", { omitirApiKey: true }).as("response");
});

Then("endpoint de consulta de acesso do perfil rejeita requisicao sem API Key", () => {
  cy.get("@response").then((response) => expect(response.status).to.eq(401));
});