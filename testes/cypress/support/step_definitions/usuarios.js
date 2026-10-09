import { When, And } from "cypress-cucumber-preprocessor/steps";

// ========================================
// DADOS DO USUÁRIO
// ========================================

When("realizo consulta de dados do usuário", () => {
  cy.getDadosUsuario().as("response");
});

And("o retorno deve conter os dados cadastrais do usuário", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body).to.have.property(
        "kc_user_id",
        Cypress.env("USUARIO_KC_USER_ID"),
      );
      expect(response.body).to.have.property(
        "username",
        Cypress.env("USUARIO_LOGIN"),
      );
      expect(response.body).to.have.property(
        "email",
        Cypress.env("USUARIO_EMAIL"),
      );
      expect(response.body).to.have.property(
        "rf",
        Cypress.env("USUARIO_RF"),
      );
    }
  });
});
