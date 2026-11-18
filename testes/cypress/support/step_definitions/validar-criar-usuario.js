import { When, Then } from "cypress-cucumber-preprocessor/steps";

When('consulto o endpoint de criação de usuário', () => {
  cy.chamarEndpointSwagger('criarUsuario').as("response");
});

When('envio criação de usuário com e-mail inválido', () => {
  cy.chamarEndpointSwagger('criarUsuarioEmailInvalido').as("response");
});

Then('a resposta de criação de usuário deve ser válida', () => {
  const expected = "400".split(",").map(Number);
  cy.get("@response").then((response) => {
    expect(expected, "status recebido: " + response.status).to.include(response.status);
  });
});
