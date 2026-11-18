import { When, And, Then } from "cypress-cucumber-preprocessor/steps";
const REFRESH_TOKEN_INVALIDO = "refresh-token-invalido";
const CHAVE_INVALIDA = "chave-invalida-automacao";

// ========================================

When("realizo logout sem informar o refresh token", () => {
  cy.postLogout(undefined).as("response");
});

When("realizo logout com refresh token vazio", () => {
  cy.postLogout("").as("response");
});

When("realizo logout sem informar a API Key", () => {
  cy.postLogout(REFRESH_TOKEN_INVALIDO, { omitirApiKey: true }).as(
    "response",
  );
});

When("realizo logout com API Key inválida", () => {
  cy.postLogout(REFRESH_TOKEN_INVALIDO, { apiKey: CHAVE_INVALIDA }).as(
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

When("consulto endpoint de logout", () => cy.chamarEndpointSwagger("logout").as("response"));
Then("endpoint de logout responde conforme esperado", () => cy.get("@response").then((r) => expect(r.status).to.eq(400)));
When("consulto endpoint de notificacao de logout", () => cy.chamarEndpointSwagger("logoutNotificacao").as("response"));
Then("endpoint de notificacao de logout responde conforme esperado", () => cy.get("@response").then((r) => expect(r.status).to.eq(400)));