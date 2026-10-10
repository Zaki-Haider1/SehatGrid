import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
const repo = resolve(process.cwd(), "..");
test.beforeEach(() =>
  execFileSync(
    "docker",
    [
      "compose",
      "-p",
      "sehat-grid-browser",
      "-f",
      "docker-compose.browser.yml",
      "exec",
      "-T",
      "api",
      "python",
      "scripts/seed_demo.py",
      "--reset",
    ],
    { cwd: repo, stdio: "pipe", timeout: 60000 },
  ),
);
async function login(page: Page, account: string) {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill(account);
  await page
    .getByLabel("Password", { exact: true })
    .fill("isolated-browser-demo-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sign out", exact: true }),
  ).toBeVisible({ timeout: 65000 });
}
async function call(page: Page, path: string, method = "GET", body?: unknown) {
  return page.evaluate(
    async ({ path, method, body }) => {
      const r = await fetch(`/api/v1/${path}`, {
        method,
        headers: {
          Authorization: `Bearer ${sessionStorage.getItem("sehat-token")}`,
          "Content-Type": "application/json",
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      return { status: r.status, json: await r.json() };
    },
    { path, method, body },
  );
}
test("3D government city supports search, layers, navigation and previous-month outcomes", async ({
  page,
}, info) => {
  await login(page, "planner");
  const map = page.locator(".pilot-map");
  await expect(map).toHaveAttribute("data-engine", "webgl-3d");
  await expect(map.locator(".city-pin")).toHaveCount(8);
  await page.screenshot({
    path: info.outputPath("government-city.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Rotate city", exact: true }).click();
  await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  await page
    .getByRole("button", { name: "Reset map view", exact: true })
    .click();
  await page.getByLabel("Search hospitals").fill("PIMS");
  await expect(page.locator(".city-hospital")).toHaveCount(1);
  await page.locator(".city-hospital").click();
  await expect(page.locator(".city-detail")).toContainText(
    "Pakistan Institute of Medical Sciences",
  );
  await page.getByRole("button", { name: "Close hospital details" }).click();
  await page.getByLabel("Search hospitals").fill("");
  await page.getByRole("button", { name: "Funding", exact: true }).click();
  await expect(map.locator('[data-hospital="P01"]')).toHaveCSS(
    "border-top-color",
    "rgb(230, 140, 146)",
  );
  await page.getByRole("button", { name: "Unmet demand", exact: true }).click();
  await expect(map.locator('[data-hospital="P02"]')).toHaveCSS(
    "border-top-color",
    "rgb(230, 140, 146)",
  );
  await page
    .getByRole("button", { name: "Review previous month", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Did the plan turn into care?" }),
  ).toBeVisible();
  await expect(
    page.getByText("No approved plan recorded for this month.", {
      exact: true,
    }),
  ).toBeVisible();
  expect(
    (await call(page, "state?month=2026-09")).json.summary.unresolved,
  ).toBe(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: info.outputPath("previous-month-outcomes.png"),
    fullPage: true,
  });
});
test("onboarder catalog saves prices and capacity, survives reload, edits and removes, and keeps roles separate", async ({
  page,
}, info) => {
  await login(page, "onboarder-p03");
  await expect(
    page.getByRole("button", { name: "Referral coordination", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Monthly planner", exact: true }),
  ).toHaveCount(0);
  const initial = await call(page, "state");
  expect(initial.json.requests).toEqual([]);
  expect(initial.json.referrals).toEqual([]);
  expect((await call(page, "requests/A-01/recommendations")).status).toBe(403);
  await page
    .getByRole("button", { name: "Services & prices", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Add service or test", exact: true })
    .click();
  await page
    .getByLabel("Service or test name", { exact: true })
    .fill("Complete blood count");
  await page.getByLabel("Price (PKR)", { exact: true }).fill("900");
  await page.getByLabel("Daily service capacity", { exact: true }).fill("30");
  await page
    .getByRole("button", { name: "Add to catalog", exact: true })
    .click();
  await expect(
    page
      .getByRole("row")
      .filter({ has: page.getByText("Complete blood count", { exact: true }) }),
  ).toContainText("PKR 900");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBeTruthy();
  await page.reload();
  await page
    .getByRole("button", { name: "Services & prices", exact: true })
    .click();
  await page.getByRole("button", { name: "Edit Complete blood count" }).click();
  await page.getByLabel("Price (PKR)", { exact: true }).fill("1200");
  await page.getByLabel("Daily service capacity", { exact: true }).fill("25");
  await page.getByRole("button", { name: "Save service changes" }).click();
  await expect(
    page
      .getByRole("row")
      .filter({ has: page.getByText("Complete blood count", { exact: true }) }),
  ).toContainText("PKR 1,200");
  const persisted = (await call(page, "state")).json.facilities.find(
    (f: { id: string }) => f.id === "P03",
  );
  expect(persisted.catalog[0]).toMatchObject({
    price: 1200,
    daily_capacity: 25,
  });
  await page.screenshot({
    path: info.outputPath("onboarding-catalog.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await login(page, "planner");
  await page
    .locator(".city-hospital")
    .filter({ hasText: "Federal Government Polyclinic" })
    .click();
  await page.locator(".city-detail").getByText("Services & prices (1)").click();
  await expect(page.locator(".city-detail")).toContainText("PKR 1,200");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await login(page, "operator-p03");
  await expect(
    page.getByRole("heading", { name: "Your reception desk" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Services & prices", exact: true }),
  ).toHaveCount(0);
  expect(
    (
      await call(page, "facilities/P03/catalog", "POST", {
        name: "Forbidden test",
        category: "Laboratory",
        price: 10,
        daily_capacity: 1,
        version: persisted.version,
      })
    ).status,
  ).toBe(403);
  await page.screenshot({
    path: info.outputPath("reception-desk.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await login(page, "onboarder-p03");
  await page
    .getByRole("button", { name: "Services & prices", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Remove Complete blood count" })
    .click();
  await expect(page.getByText("Your services start here.")).toBeVisible();
  expect(
    (await call(page, "state")).json.facilities.find(
      (f: { id: string }) => f.id === "P03",
    ).catalog,
  ).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBeTruthy();
});
