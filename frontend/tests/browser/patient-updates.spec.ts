import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

test("consented confirmation opens a separate patient demo; private reception cannot send", async ({
  page,
  request,
}, info) => {
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
    { cwd: resolve(process.cwd(), ".."), timeout: 60000 },
  );
  const password = "isolated-browser-demo-password";
  const tokens: Record<string, string> = {};
  async function call(user: string, path: string, body?: unknown) {
    if (!tokens[user]) {
      const r = await request.post("/api/v1/auth/login", {
        data: { username: user, password },
      });
      expect(r.ok()).toBeTruthy();
      tokens[user] = (await r.json()).token;
    }
    const r = await request.fetch(`/api/v1/${path}`, {
      method: body ? "POST" : "GET",
      headers: {
        Authorization: `Bearer ${tokens[user]}`,
        "Idempotency-Key": crypto.randomUUID(),
      },
      data: body,
    });
    expect(r.ok(), await r.text()).toBeTruthy();
    return r.json();
  }
  const sender = "operator-p08",
    state = await call(sender, "state");
  const match = await call(sender, "matching/services", {
    text: "general doctor consultation",
  });
  const review = await call(sender, "matching/reviews", {
    match_id: match.id,
    decision: "ACCEPT",
    candidate_id: "PRIMARY_CARE_OPD",
    reason: "Staff reviewed the service",
  });
  const patient = await call(sender, "requests", {
    reference: "WHATSAPP-DEMO",
    source_facility_id: "P08",
    zone: "South",
    original_text: "general doctor consultation",
    review_id: review.id,
    date_from: state.config.service_date,
    date_to: state.config.service_date,
    suitable: true,
    whatsapp_phone: "+923000000000",
    whatsapp_consent: true,
  });
  const choice = (await call(sender, `requests/${patient.id}/recommendations`))
    .candidates[0];
  const referral = await call(sender, "referrals/proposals", {
    request_id: patient.id,
    capacity_id: choice.capacity_id,
    capacity_version: choice.capacity_version,
    facility_version: choice.facility_version,
  });
  await call(sender, `referrals/${referral.id}/reserve`, {});
  expect((await call(sender, "state")).notifications).toHaveLength(0);
  await call("operator-p01", `referrals/${referral.id}/partner-response`, {
    accepted: true,
  });
  await call(sender, `referrals/${referral.id}/patient-agreement`, {
    accepted: true,
  });
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill(sender);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page
    .getByRole("button", { name: "Referral coordination", exact: true })
    .click();
  const opened = page.waitForEvent("popup");
  await page
    .getByRole("button", { name: "Open patient message demo ↗" })
    .click();
  const preview = await opened;
  await expect(preview.locator(".chat-bubble")).toHaveCount(1);
  await expect(preview.locator(".chat-bubble")).toContainText(
    "Shifa International Hospital",
  );
  await call(sender, `referrals/${referral.id}/cancel`, {
    reason: "Sending hospital is reviewing a replacement",
  });
  await expect(preview.locator(".chat-bubble")).toHaveCount(2, {
    timeout: 15000,
  });
  await expect(
    preview.getByText("Simulation only · No messages are sent to WhatsApp."),
  ).toBeVisible();
  await preview.screenshot({
    path: info.outputPath("patient-messages.png"),
    fullPage: true,
  });
  expect(
    await preview.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBeTruthy();
  await preview.close();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page.getByLabel("Username", { exact: true }).fill("operator-p01");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page
    .getByRole("button", { name: "Receiving desk", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Register request", exact: true }),
  ).toHaveCount(0);
  const blocked = await request.post("/api/v1/requests", {
    headers: {
      Authorization: `Bearer ${tokens["operator-p01"]}`,
      "Idempotency-Key": crypto.randomUUID(),
    },
    data: {
      reference: "BLOCKED",
      source_facility_id: "P01",
      zone: "South",
      original_text: "consultation",
      date_from: state.config.service_date,
      date_to: state.config.service_date,
      suitable: true,
    },
  });
  expect(blocked.status()).toBe(403);
});
