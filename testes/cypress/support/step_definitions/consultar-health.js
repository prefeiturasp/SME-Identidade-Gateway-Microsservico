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

Then('a resposta de health check deve informar o estado da aplicação e dependências', () => {
  cy.get("@response").then((response) => {
    expect(response.status).to.eq(200);
    expect(response.body.status).to.eq("healthy");
    expect(response.body.dependencias.token_ms).to.be.oneOf([
      "healthy",
      "degraded",
      "unhealthy",
    ]);
  });
});
