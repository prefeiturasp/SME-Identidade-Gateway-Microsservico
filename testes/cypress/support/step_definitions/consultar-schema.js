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

Then('o schema deve documentar o endpoint de alteração de e-mail', () => {
  cy.get("@response").then((response) => {
    expect(response.status).to.eq(200);
    expect(response.body).to.have.property("openapi");
    const paths = Object.keys(response.body.paths);
    expect(
      paths.some((path) => path.endsWith("/autenticacao/alterar-email/")),
    ).to.eq(true);
  });
});
