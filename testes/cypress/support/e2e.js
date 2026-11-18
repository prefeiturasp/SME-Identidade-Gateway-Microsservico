import "@shelex/cypress-allure-plugin";

// Comandos
import "./commands_api/commands_autenticacao";
import "./commands_api/commands_usuarios";
import "./commands_api/commands_perfis";
import "./commands_api/commands_sistemas";
import "./commands_api/commands_endpointos";

// Evita quebra de teste
Cypress.on("uncaught:exception", () => false);
