import { When, And } from "cypress-cucumber-preprocessor/steps";

const CHAVE_INVALIDA = "chave-invalida-automacao";
const REFRESH_TOKEN_INVALIDO = "refresh-token-invalido";

// ========================================
// LOGIN
// ========================================

When("realizo login com credenciais válidas", () => {
  cy.postLogin().as("response");
});

When("realizo login com senha inválida", () => {
  cy.postLogin({ senha: Cypress.env("USUARIO_SENHA_INVALIDA") }).as(
    "response",
  );
});

When("realizo login sem informar a senha", () => {
  cy.postLogin({ omitirSenha: true }).as("response");
});

When("realizo login sem informar o login", () => {
  cy.postLogin({ omitirLogin: true }).as("response");
});

When("realizo login sem informar a API Key", () => {
  cy.postLogin({ omitirApiKey: true }).as("response");
});

When("realizo login com API Key inválida", () => {
  cy.postLogin({ apiKey: CHAVE_INVALIDA }).as("response");
});

And("o retorno deve conter os dados da sessão do usuário", () => {
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
      expect(response.body).to.have.property("rf", Cypress.env("USUARIO_RF"));
      expect(response.body).to.have.property("ativo", true);
      expect(response.body.access_token).to.be.a("string").and.not.be.empty;
      expect(response.body.refresh_token).to.be.a("string").and.not.be.empty;
      expect(response.body).to.have.property("roles");
      expect(response.body.roles).to.be.an("object");
    }
  });
});

// ========================================
// LOGOUT
// ========================================

When("realizo logout sem informar o refresh token", () => {
  cy.postLogout(undefined).as("response");
});

When("realizo logout sem informar a API Key", () => {
  cy.postLogout(REFRESH_TOKEN_INVALIDO, { omitirApiKey: true }).as(
    "response",
  );
});

When("realizo logout com refresh token inválido", () => {
  cy.postLogout(REFRESH_TOKEN_INVALIDO).as("response");
});

When("realizo logout com o refresh token obtido no login", () => {
  cy.postLogin().then((login) => {
    expect(login.status, "status do login").to.eq(200);
    cy.postLogout(login.body.refresh_token).as("response");
  });
});

And("o retorno deve confirmar o encerramento da sessão", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body).to.have.property("situacao", "sessao_encerrada");
    }
  });
});

// ========================================
// VALIDAR TOKEN ENRIQUECIDO
// ========================================

When("valido o token enriquecido sem informar o token", () => {
  cy.postValidarToken(undefined).as("response");
});

When("valido o token enriquecido sem informar a API Key", () => {
  cy.postValidarToken("token-qualquer", { omitirApiKey: true }).as(
    "response",
  );
});
