import { When } from "cypress-cucumber-preprocessor/steps";

// ========================================
// LOGIN
// ========================================

When("realizo login com senha inválida", () => {
  cy.postLogin({ senha: Cypress.env("USUARIO_SENHA_INVALIDA") }).as(
    "response",
  );
});

When("realizo login sem informar a senha", () => {
  cy.postLogin({ omitirSenha: true }).as("response");
});

When("realizo login sem informar a API Key", () => {
  cy.postLogin({ omitirApiKey: true }).as("response");
});

// ========================================
// LOGOUT
// ========================================

When("realizo logout sem informar o refresh token", () => {
  cy.postLogout(undefined).as("response");
});
