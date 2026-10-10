import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
const repo = resolve(process.cwd(), "..");
test("changed capacity expires a proposal and reception shows recovery instead of a hold", async ({
  page,
  context,
}) => {
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
  );
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill("operator-p08");
  await page
    .getByLabel("Password", { exact: true })
    .fill("isolated-browser-demo-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sign out", exact: true }),
  ).toBeVisible({ timeout: 65000 });
  await page
    .getByRole("button", { name: "Referral coordination", exact: true })
    .click();
  const row = page
    .getByRole("row")
    .filter({ has: page.getByText("A-01", { exact: true }) });
  await row
    .getByRole("button", { name: "Find providers", exact: true })
    .click();
  const option = page
    .locator(".recommendation")
    .filter({ hasText: "Shifa International Hospital" });
  const proposalResponse = page.waitForResponse(
    (r) =>
      r.url().includes("/api/v1/referrals/proposals") &&
      r.request().method() === "POST",
  );
  await option.getByRole("button", { name: "Save referral proposal" }).click();
  const proposal = await (await proposalResponse).json();
  const other = await context.newPage();
  await other.goto("/");
  await other.getByLabel("Username", { exact: true }).fill("onboarder-p01");
  await other
    .getByLabel("Password", { exact: true })
    .fill("isolated-browser-demo-password");
  await other.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    other.getByRole("button", { name: "Sign out", exact: true }),
  ).toBeVisible({ timeout: 65000 });
  await other.getByLabel("Declared network quota", { exact: true }).fill("9");
  await other
    .getByRole("button", { name: "Update dated quota", exact: true })
    .click();
  await expect(other.getByRole("status")).toBeVisible();
  const attempt = page
    .locator(".referral")
    .filter({ has: page.getByText(new RegExp(`^${proposal.id} →`)) });
  await attempt
    .getByRole("button", { name: "Approve & reserve proposal", exact: true })
    .click();
  await expect(page.locator('.error[role="alert"]')).toContainText(
    "This proposal expired because its inputs changed.",
  );
  await expect(attempt.locator(".badge")).toHaveText("expired");
  await expect(
    row.getByRole("button", { name: "Find providers", exact: true }),
  ).toBeVisible();
  const state = await other.evaluate(async () => {
    const r = await fetch("/api/v1/state", {
      headers: {
        Authorization: `Bearer ${sessionStorage.getItem("sehat-token")}`,
      },
    });
    return r.json();
  });
  expect(
    state.facilities.find((f: { id: string }) => f.id === "P01").capacities[0]
      .held,
  ).toBe(0);
  await other.close();
});
