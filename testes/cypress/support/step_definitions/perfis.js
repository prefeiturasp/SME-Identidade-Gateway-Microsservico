import { When, And } from "cypress-cucumber-preprocessor/steps";

// ========================================
// PERFIS
// ========================================

When("realizo consulta de perfis do usuário", () => {
  cy.getPerfisPorLogin().as("response");
});

And("o retorno deve conter a lista de perfis", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body).to.have.property("perfis");
      expect(response.body.perfis).to.be.an("array");
    }
  });
});

// ========================================
// DADOS DE ACESSO (PERFIL)
// ========================================

When("realizo consulta de dados de acesso do perfil do usuário", () => {
  cy.getDadosAcesso().as("response");
});

And("o retorno deve conter o token e as permissões do perfil", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body).to.have.property("token");
      expect(response.body).to.have.property("data_expiracao_token");
      expect(response.body).to.have.property("permissoes");
      expect(response.body.permissoes).to.be.an("array");
    }
  });
});
