import { defineConfig } from "cypress";
import allureWriter from "@shelex/cypress-allure-plugin/writer.js";
import { cloudPlugin } from "cypress-cloud/plugin";
import dotenv from "dotenv";
import cucumber from "cypress-cucumber-preprocessor";
import preprocessor from "@cypress/webpack-preprocessor";
import postgreSQL from "cypress-postgresql";
import pg from "pg";
import fs from "fs";
import FormData from "form-data";
import axios from "axios";

dotenv.config();

const dbConfig = {
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  host: process.env.DB_HOST,
  database: process.env.DB_DATABASE,
};

const envKeys = [
  "API_URL",
  "API_KEY",
  "API_KEY_HEADER",
  "USUARIO_LOGIN",
  "USUARIO_SENHA",
  "USUARIO_SENHA_INVALIDA",
  "USUARIO_NOME",
  "USUARIO_EMAIL",
  "USUARIO_CPF",
  "USUARIO_RF",
  "USUARIO_KC_USER_ID",
  "USUARIO_PERFIL",
  "ADMIN_URL",
  "ADMIN_LOGIN",
  "ADMIN_PASSWORD",
];

const adminUiConfigured = ["ADMIN_URL", "ADMIN_LOGIN", "ADMIN_PASSWORD"].every(
  (key) => Boolean(process.env[key]),
);

export default defineConfig({
  e2e: {
    watchForFileChanges: true,

    supportFile: "cypress/support/e2e.js",

    viewportWidth: 1920,
    viewportHeight: 1080,
    video: false,

    retries: {
      runMode: 2,
      openMode: 0,
    },

    screenshotOnRunFailure: false,
    chromeWebSecurity: false,
    experimentalRunAllSpecs: true,
    failOnStatusCode: false,

    specPattern: ["cypress/e2e/**/*.feature"],

    defaultCommandTimeout: 60000,
    requestTimeout: 60000,
    execTimeout: 60000,
    pageLoadTimeout: 60000,

    env: {
      allure: true,
      // IGNORA TAGS @ignore
      TAGS: adminUiConfigured ? "not @ignore" : "not @ignore and not @admin-ui",
    },

    async setupNodeEvents(on, config) {
      allureWriter(on, config);

      config.env.allure = true;

      const webpackConfig = {
        module: {
          rules: [
            {
              test: /\.js$/,
              exclude: [/node_modules/],
              use: {
                loader: "babel-loader",
                options: {
                  plugins: ["@babel/plugin-transform-modules-commonjs"],
                },
              },
            },
          ],
        },
      };

      on(
        "file:preprocessor",
        preprocessor({
          webpackOptions: webpackConfig,
        }),
      );

      on("file:preprocessor", cucumber.default());

      // =========================
      // BANCO
      // =========================

      const pool = new pg.Pool(dbConfig);
      const dbTasks = postgreSQL.loadDBPlugin(pool);

      on("task", {
        ...dbTasks,

        async uploadFile({ method = "POST", url, headers = {}, filePath }) {
          const form = new FormData();

          if (filePath && filePath.trim() !== "") {
            form.append("file", fs.createReadStream(filePath));
          }

          const response = await axios({
            method,
            url,
            headers: {
              ...headers,
              ...form.getHeaders(),
            },
            data: form,
            maxBodyLength: Infinity,
            validateStatus: () => true,
          });

          return {
            status: response.status,
            body: response.data,
          };
        },
      });

      // =========================
      // ENV
      // =========================

      const customVariable = Object.fromEntries(
        envKeys.map((key) => [key, process.env[key] ?? ""]),
      );

      config.env = {
        ...config.env,
        ...customVariable,
        db: dbConfig,
      };

      // =========================
      // BASE URL
      // =========================

      config.baseUrl = process.env.API_URL;

      return await cloudPlugin(on, config);
    },
  },
});
