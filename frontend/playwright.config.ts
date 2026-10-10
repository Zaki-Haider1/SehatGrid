import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/browser",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: !!process.env.CI,
  timeout: 300_000,
  expect: { timeout: 15_000 },
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/browser-results.json" }],
    ["html", { open: "never" }],
  ],
  use: {
    actionTimeout: 30_000,
    baseURL: "http://127.0.0.1:13000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    browserName: "chromium",
    launchOptions: {
      args: [
        "--use-gl=angle",
        "--use-angle=swiftshader-webgl",
        "--enable-unsafe-swiftshader",
      ],
    },
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 1000 } } },
    {
      name: "phone",
      use: {
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
  webServer: {
    command: "npm start",
    url: "http://127.0.0.1:13000",
    reuseExistingServer: false,
    timeout: 120_000,
    env: { PORT: "13000", HOSTNAME: "127.0.0.1" },
  },
});
