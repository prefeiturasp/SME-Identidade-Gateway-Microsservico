import { When, And } from "cypress-cucumber-preprocessor/steps";

const CHAVE_INVALIDA = "chave-invalida-automacao";

// ========================================
// PERFIS
// ========================================

When("realizo consulta de perfis do usuário", () => {
  cy.getPerfisPorLogin().as("response");
});

When("realizo consulta de perfis do usuário sem informar a API Key", () => {
  cy.getPerfisPorLogin({ omitirApiKey: true }).as("response");
});

When("realizo consulta de perfis do usuário com API Key inválida", () => {
  cy.getPerfisPorLogin({ apiKey: CHAVE_INVALIDA }).as("response");
});

And("o retorno deve conter a lista de perfis", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body).to.have.property("perfis");
      expect(response.body.perfis).to.be.an("array");
    }
  });
});

And("o retorno deve conter o RF do usuário e perfis com estrutura válida", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body).to.have.property("rf", Cypress.env("USUARIO_RF"));
      expect(response.body.perfis).to.be.an("array");
      response.body.perfis.forEach((perfil) => {
        expect(perfil).to.have.all.keys("id", "sistema_id", "nome", "ativo");
        expect(perfil.id).to.be.a("string").and.not.be.empty;
        if (perfil.sistema_id !== null) {
          expect(perfil.sistema_id).to.be.a("number");
        }
        expect(perfil.nome).to.be.a("string").and.not.be.empty;
        expect(perfil.ativo).to.be.a("boolean");
      });
    }
  });
});

// ========================================
// DADOS DE ACESSO (PERFIL)
// ========================================

When("realizo consulta de dados de acesso do perfil do usuário", () => {
  cy.getDadosAcesso().as("response");
});

When(
  "realizo consulta de dados de acesso do perfil do usuário sem informar a API Key",
  () => {
    cy.getDadosAcesso({ omitirApiKey: true }).as("response");
  },
);

When(
  "realizo consulta de dados de acesso do perfil do usuário com API Key inválida",
  () => {
    cy.getDadosAcesso({ apiKey: CHAVE_INVALIDA }).as("response");
  },
);

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

And("as permissões do perfil devem ter estrutura válida", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body.permissoes).to.be.an("array");
      response.body.permissoes.forEach((permissao) => {
        expect(permissao).to.have.all.keys(
          "sistema_id",
          "sistema_nome",
          "modulo_id",
          "modulo_nome",
          "consultar",
          "inserir",
          "alterar",
          "excluir",
        );
        expect(permissao.sistema_id).to.be.a("number");
        expect(permissao.modulo_id).to.be.a("number");
        expect(permissao.consultar).to.be.a("boolean");
        expect(permissao.inserir).to.be.a("boolean");
        expect(permissao.alterar).to.be.a("boolean");
        expect(permissao.excluir).to.be.a("boolean");
      });
    }
  });
});
