import { When, And } from "cypress-cucumber-preprocessor/steps";

const CHAVE_INVALIDA = "chave-invalida-automacao";

// ========================================
// SISTEMAS
// ========================================

When("realizo consulta de sistemas do usuário", () => {
  cy.getSistemasPorLogin().as("response");
});

When("realizo consulta de sistemas do usuário sem informar a API Key", () => {
  cy.getSistemasPorLogin({ omitirApiKey: true }).as("response");
});

When("realizo consulta de sistemas do usuário com API Key inválida", () => {
  cy.getSistemasPorLogin({ apiKey: CHAVE_INVALIDA }).as("response");
});

And("o retorno deve conter a lista de sistemas", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body).to.have.property("sistemas");
      expect(response.body.sistemas).to.be.an("array");
    }
  });
});

And("os sistemas do usuário devem ter estrutura válida", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body.sistemas).to.be.an("array");
      response.body.sistemas.forEach((sistema) => {
        expect(sistema).to.have.all.keys("sistema_id", "sistema_nome");
        expect(sistema.sistema_id).to.be.a("number");
        expect(sistema.sistema_nome).to.be.a("string").and.not.be.empty;
      });
    }
  });
});
