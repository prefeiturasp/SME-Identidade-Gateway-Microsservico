import { Then } from "cypress-cucumber-preprocessor/steps";

Then("os principais elementos do painel devem estar visíveis", () => {
  [
    "Painel de controle",
    "Dashboard",
    "Identidades",
    "Sistemas (Clients)",
    "Blueprints",
    "Realms ativos",
    "Usuários base",
    "Topologia oficial SME",
    "COTIC",
    "sme-apps",
    "master",
    "Outros / testes",
    "Nome do realm",
    "Status",
    "Ações",
  ].forEach((text) => {
    cy.contains(text).should("be.visible");
  });
});
