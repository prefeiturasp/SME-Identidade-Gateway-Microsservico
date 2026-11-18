import { When, Then } from "cypress-cucumber-preprocessor/steps";

When('consulto o endpoint de consulta de usuário', () => {
  cy.chamarEndpointSwagger('consultarUsuario').as("response");
});

When('consulto endpoint de consulta de usuário com API Key inválida', () => {
  cy.chamarEndpointSwagger('consultarUsuario', {
    apiKey: "chave-invalida-automacao",
  }).as("response");
});

Then('a resposta de consulta de usuário deve ser válida', () => {
  const expected = "200,204".split(",").map(Number);
  cy.get("@response").then((response) => {
    expect(expected, "status recebido: " + response.status).to.include(response.status);
  });
});
