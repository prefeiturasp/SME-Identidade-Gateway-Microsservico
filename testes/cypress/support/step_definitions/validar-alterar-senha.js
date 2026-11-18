import { When, Then } from "cypress-cucumber-preprocessor/steps";

When('consulto o endpoint de alteração de senha', () => {
  cy.chamarEndpointSwagger('alterarSenha').as("response");
});

When('consulto o endpoint de alteração de senha sem enviar dados', () => {
  cy.chamarEndpointSwagger('alterarSenhaSemDados').as("response");
});

When('envio solicitação de alteração de senha com senha vazia', () => {
  cy.chamarEndpointSwagger('alterarSenhaVazia').as("response");
});

Then('a resposta de alteração de senha deve ser válida', () => {
  const expected = "400".split(",").map(Number);
  cy.get("@response").then((response) => {
    expect(expected, "status recebido: " + response.status).to.include(response.status);
  });
});
