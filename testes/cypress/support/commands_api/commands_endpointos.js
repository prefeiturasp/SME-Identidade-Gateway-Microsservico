const baseUrl = () => Cypress.env("API_URL");

const apiHeaders = (options = {}) => {
  const headers = {
    accept: "application/json",
    "Content-Type": "application/json",
  };

  if (!options.omitirApiKey) {
    headers[Cypress.env("API_KEY_HEADER")] =
      options.apiKey !== undefined ? options.apiKey : Cypress.env("API_KEY");
  }

  return headers;
};

Cypress.Commands.add("chamarEndpointSwagger", (endpoint, options = {}) => {
  const login = encodeURIComponent(
    options.login !== undefined ? options.login : Cypress.env("USUARIO_LOGIN"),
  );
  const perfil = encodeURIComponent(
    options.perfil !== undefined
      ? options.perfil
      : Cypress.env("USUARIO_PERFIL"),
  );
  const email = encodeURIComponent(Cypress.env("USUARIO_EMAIL"));
  const requests = {
    alterarEmail: ["POST", "/autenticacao/alterar-email/", {}],
    alterarEmailInvalido: [
      "POST",
      "/autenticacao/alterar-email/",
      { login: "cypress-validacao-invalida", email: "email-invalido" },
    ],
    alterarSenha: ["POST", "/autenticacao/alterar-senha/", {}],
    alterarSenhaVazia: [
      "POST",
      "/autenticacao/alterar-senha/",
      { login: "cypress-validacao-invalida", senha: "" },
    ],
    alterarSenhaSemDados: ["POST", "/autenticacao/alterar-senha/"],
    loginCliente: ["POST", "/autenticacao/cliente/login/", {}],
    validarTokenCliente: ["POST", "/autenticacao/cliente/validar-token/", {}],
    validarTokenClienteVazio: [
      "POST",
      "/autenticacao/cliente/validar-token/",
      { token: "" },
    ],
    login: ["POST", "/autenticacao/login/", {}],
    logout: ["POST", "/autenticacao/logout/", {}],
    logoutNotificacao: ["POST", "/autenticacao/logout-notificacao/", {}],
    dadosUsuario: ["GET", `/autenticacao/usuarios/${login}/dados/`],
    validarToken: ["POST", "/autenticacao/validar-token/", {}],
    perfis: ["GET", `/autenticacao/usuarios/${login}/perfis/`],
    acessoPerfil: ["GET", `/autenticacao/usuarios/${login}/perfis/${perfil}/acesso/`],
    sistemas: ["GET", `/autenticacao/usuarios/${login}/sistemas/`],
    health: ["GET", "/health/"],
    schema: ["GET", "/schema/"],
    criarUsuario: ["POST", "/usuarios/", {}],
    criarUsuarioEmailInvalido: [
      "POST",
      "/usuarios/",
      {
        nome: "Usuario Cypress",
        email: "email-invalido",
        rf: "cypress-validacao-invalida",
      },
    ],
    concederAcesso: ["POST", "/usuarios/conceder-acesso/", {}],
    concederAcessoRolesVazias: [
      "POST",
      "/usuarios/conceder-acesso/",
      {
        identificador: "cypress-validacao-invalida",
        sistema: 1,
        roles: [],
      },
    ],
    consultarUsuario: ["GET", `/usuarios/consultar/?email=${email}`],
    sincronizarUsuario: ["POST", "/usuarios/sincronizar/", {}],
    sincronizarUsuarioSemIdentificador: [
      "POST",
      "/usuarios/sincronizar/",
      { identificador: "" },
    ],
  };

  const request = requests[endpoint];
  if (!request) throw new Error(`Endpoint Swagger desconhecido: ${endpoint}`);

  const [method, path, body] = request;
  return cy.request({
    method,
    url: `${baseUrl()}${path}`,
    headers: apiHeaders(options),
    ...(body ? { body } : {}),
    failOnStatusCode: false,
  });
});
