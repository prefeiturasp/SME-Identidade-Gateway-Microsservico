import { When, Then } from "cypress-cucumber-preprocessor/steps";

// ========================================

When("valido o token enriquecido sem informar o token", () => {
  cy.postValidarToken(undefined).as("response");
});

When("valido o token enriquecido vazio", () => {
  cy.postValidarToken("").as("response");
});

When("valido o token enriquecido sem informar a API Key", () => {
  cy.postValidarToken("token-qualquer", { omitirApiKey: true }).as(
    "response",
  );
});

When("consulto endpoint de validacao de token", () => cy.chamarEndpointSwagger("validarToken").as("response"));
Then("endpoint de validacao de token responde conforme esperado", () => cy.get("@response").then((r) => expect(r.status).to.eq(400)));