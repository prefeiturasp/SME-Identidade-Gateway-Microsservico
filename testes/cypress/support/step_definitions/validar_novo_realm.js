import { Then, When } from "cypress-cucumber-preprocessor/steps";

const getControlByLabel = (labelText) => {
  return cy
    .contains("label", labelText)
    .should("be.visible")
    .invoke("attr", "for")
    .then((controlId) => {
      expect(controlId, `campo associado ao rótulo "${labelText}"`)
        .to.be.a("string")
        .and.not.be.empty;
      return cy.get(`#${controlId}`).should("be.visible");
    });
};

When("abro o formulário de novo realm", () => {
  cy.contains("button", "Novo realm (Provisionar)")
    .should("be.visible")
    .click();
});

Then("os campos e opções do novo realm devem estar visíveis", () => {
  cy.contains("Novo realm").should("be.visible");

  getControlByLabel("Nome do realm")
    .should("match", "input")
    .should(($input) => expect($input[0].type).to.equal("text"));
  getControlByLabel("Nome de exibição")
    .should("match", "input")
    .should(($input) => expect($input[0].type).to.equal("text"));
  getControlByLabel("Finalidade").should("match", "select");

  cy.contains("Topologia oficial SME").should("be.visible");
  cy.get('input[type="checkbox"]').should("be.visible");
  cy.contains("Situação").should("be.visible");
  cy.contains("label", "Habilitado").should("be.visible");
  cy.contains("label", "Desabilitado").should("be.visible");
  cy.get('input[type="radio"]').should("have.length", 2);

  cy.contains("button", /^Cancelar$/).should("be.visible");
  cy.contains("button", /^Salvar$/).should("be.visible");
});
