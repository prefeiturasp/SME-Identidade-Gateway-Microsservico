import { When, And, Then } from "cypress-cucumber-preprocessor/steps";
const CHAVE_INVALIDA = "chave-invalida-automacao";

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

When("realizo login com senha vazia", () => {
  cy.postLogin({ senha: "" }).as("response");
});

When("realizo login com login vazio", () => {
  cy.postLogin({ login: "" }).as("response");
});

When("realizo login com login nulo", () => {
  cy.postLogin({ login: null }).as("response");
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

When("consulto endpoint de login de usuario", () => cy.chamarEndpointSwagger("login").as("response"));
Then("endpoint de login de usuario responde conforme esperado", () => cy.get("@response").then((r) => expect(r.status).to.eq(400)));
When("consulto endpoint de login de cliente", () => cy.chamarEndpointSwagger("loginCliente").as("response"));
Then("endpoint de login de cliente responde conforme esperado", () => cy.get("@response").then((r) => expect(r.status).to.eq(400)));