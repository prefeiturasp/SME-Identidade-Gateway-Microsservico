import { When, And } from "cypress-cucumber-preprocessor/steps";

// ========================================
// SISTEMAS
// ========================================

When("realizo consulta de sistemas do usuário", () => {
  cy.getSistemasPorLogin().as("response");
});

And("o retorno deve conter a lista de sistemas", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body).to.have.property("sistemas");
      expect(response.body.sistemas).to.be.an("array");
    }
  });
});
