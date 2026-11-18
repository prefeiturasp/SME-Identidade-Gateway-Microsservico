import { When, And } from "cypress-cucumber-preprocessor/steps";

const CHAVE_INVALIDA = "chave-invalida-automacao";

// ========================================
// DADOS DO USUÁRIO
// ========================================

When("realizo consulta de dados do usuário", () => {
  cy.getDadosUsuario().as("response");
});

When("realizo consulta de dados do usuário sem informar a API Key", () => {
  cy.getDadosUsuario({ omitirApiKey: true }).as("response");
});

When("realizo consulta de dados do usuário com API Key inválida", () => {
  cy.getDadosUsuario({ apiKey: CHAVE_INVALIDA }).as("response");
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

And("o retorno deve conter o CPF e o nome cadastrados do usuário", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body).to.have.property(
        "cpf",
        Cypress.env("USUARIO_CPF"),
      );
      expect(response.body).to.have.property(
        "nome",
        Cypress.env("USUARIO_NOME"),
      );
      expect(response.body).to.have.property("ativo", true);
    }
  });
});
