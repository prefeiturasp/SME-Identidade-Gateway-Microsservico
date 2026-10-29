import { Given, When, Then } from "cypress-cucumber-preprocessor/steps";

const getCredential = (name) => {
  const value = Cypress.env(name);
  expect(value, `variável ${name} no arquivo .env`)
    .to.be.a("string")
    .and.not.be.empty;
  return value;
};

const getInputByLabel = (labelText) => {
  return cy
    .contains("label", new RegExp(`^${labelText}$`))
    .should("be.visible")
    .invoke("attr", "for")
    .then((inputId) => {
      expect(inputId, `campo associado ao rótulo "${labelText}"`)
        .to.be.a("string")
        .and.not.be.empty;
      return cy.get(`#${inputId}`);
    });
};

const fillUsername = () => {
  getInputByLabel("Usuário")
    .clear()
    .type(getCredential("ADMIN_LOGIN"), { log: false });
};

const fillPassword = () => {
  getInputByLabel("Senha")
    .clear()
    .type(getCredential("ADMIN_PASSWORD"), { log: false });
};

Given("que estou na tela de login do painel administrativo", () => {
  const loginUrl = getCredential("ADMIN_URL");
  expect(loginUrl).to.match(/^https?:\/\//);

  cy.visit(loginUrl);
  cy.contains("h1", "Entrar").should("be.visible");
});

When("preencho as credenciais cadastradas", () => {
  fillUsername();
  fillPassword();
});

When("preencho a senha cadastrada", () => {
  fillPassword();
});

When("alterno a exibição da senha", () => {
  cy.get('button[aria-label="Mostrar senha"], button[aria-label="Ocultar senha"]')
    .should("be.visible")
    .click();
});

When("envio o formulário de login", () => {
  cy.contains("button", /^Entrar$/).click();
});

Then("os campos de usuário e senha devem estar visíveis", () => {
  getInputByLabel("Usuário").should("be.visible");
  getInputByLabel("Senha").should("be.visible");
});

Then("o botão Entrar deve estar desabilitado", () => {
  cy.contains("button", /^Entrar$/).should("be.disabled");
});

Then("o botão Entrar deve estar habilitado", () => {
  cy.contains("button", /^Entrar$/).should("be.enabled");
});

Then("a senha deve ficar visível", () => {
  getInputByLabel("Senha").should("be.visible").and("have.attr", "type", "text");
});

Then("a senha deve ficar oculta", () => {
  getInputByLabel("Senha")
    .should("be.visible")
    .and("have.attr", "type", "password");
});

Then("devo sair da tela de login", () => {
  cy.location("pathname").should("not.include", "/admin/login");
});
