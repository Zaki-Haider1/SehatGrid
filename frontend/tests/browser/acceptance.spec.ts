import { test, expect, type Page, type Locator } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import type { State, Plan } from "../../lib/api";

const repo = resolve(process.cwd(), "..");
const password = "isolated-browser-demo-password";
const compose = [
  "compose",
  "-p",
  "sehat-grid-browser",
  "-f",
  "docker-compose.browser.yml",
];
test.beforeEach(() => {
  // This command can only reach the dedicated acceptance container.
  execFileSync(
    "docker",
    [
      ...compose,
      "exec",
      "-T",
      "api",
      "python",
      "scripts/seed_demo.py",
      "--reset",
    ],
    { cwd: repo, stdio: "pipe", timeout: 60_000 },
  );
});

function card(page: Page, title: string) {
  return page
    .locator("section.card")
    .filter({ has: page.getByRole("heading", { name: title, exact: true }) });
}
async function login(page: Page, account: string) {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill(account);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sign out", exact: true }),
  ).toBeVisible({ timeout: 65_000 });
}
async function switchRole(page: Page, account: string) {
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await login(page, account);
}
async function saved(page: Page, button: Locator, path: string) {
  const response = page.waitForResponse(
    (r) =>
      r.url().includes(`/api/v1/${path}`) && r.request().method() !== "GET",
  );
  const refreshed = page.waitForResponse(
    (r) => r.url().includes("/api/v1/state") && r.request().method() === "GET",
  );
  await button.click();
  const result = await response;
  expect(result.ok(), await result.text()).toBeTruthy();
  const json = await result.json();
  await refreshed;
  await expect(page.getByRole("status")).toBeVisible();
  return json;
}
async function state(page: Page): Promise<State> {
  return page.evaluate(async () => {
    const response = await fetch("/api/v1/state", {
      headers: {
        Authorization: `Bearer ${sessionStorage.getItem("sehat-token")}`,
      },
    });
    if (!response.ok) throw new Error(`State read failed: ${response.status}`);
    return response.json();
  });
}
async function responsive(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBeTruthy();
}
async function reserve(
  page: Page,
  reference: string,
  facility: string,
  reload = false,
) {
  const row = page
    .getByRole("row")
    .filter({ has: page.getByText(reference, { exact: true }) });
  await row
    .getByRole("button", { name: "Find providers", exact: true })
    .click();
  const option = page.locator(`.recommendation[data-facility="${facility}"]`);
  await expect(option.getByText(/referral-ranking-v/)).toBeVisible();
  const before = await state(page);
  const proposal = await saved(
    page,
    option.getByRole("button", { name: "Save referral proposal" }),
    "referrals/proposals",
  );
  expect(proposal.status).toBe("PROPOSED");
  const after = await state(page);
  expect(after.facilities.map((f) => f.capacities)).toEqual(
    before.facilities.map((f) => f.capacities),
  );
  if (reload) {
    await page.reload();
    await page
      .getByRole("button", {
        name: /^(Referral coordination|Receiving desk)$/,
        exact: true,
      })
      .click();
  }
  await expect(referral(page, proposal.id).locator(".badge")).toHaveText(
    "proposed",
  );
  const reserved = await saved(
    page,
    referral(page, proposal.id).getByRole("button", {
      name: "Approve & reserve proposal",
      exact: true,
    }),
    `referrals/${proposal.id}/reserve`,
  );
  await switchRole(page, `operator-${facility.toLowerCase()}`);
  await page
    .getByRole("button", { name: /^(Referral coordination|Receiving desk)$/ })
    .click();
  return reserved;
}
function referral(page: Page, id: string) {
  return page
    .locator(".referral")
    .filter({ has: page.getByText(new RegExp(`^${id} →`)) });
}
async function complete(page: Page, id: string) {
  const current = await state(page);
  const destination = current.referrals.find((a) => a.id === id)!.facility_id;
  if (!current.user.facility_ids.includes(destination)) {
    await switchRole(page, `operator-${destination.toLowerCase()}`);
    await page
      .getByRole("button", { name: /^(Referral coordination|Receiving desk)$/ })
      .click();
  }
  await saved(
    page,
    referral(page, id).getByRole("button", {
      name: "Record arrival",
      exact: true,
    }),
    `referrals/${id}/arrival`,
  );
  await expect(referral(page, id).locator(".badge")).toHaveText("arrived");
  await saved(
    page,
    referral(page, id).getByRole("button", {
      name: "Complete service",
      exact: true,
    }),
    `referrals/${id}/completion`,
  );
  await expect(referral(page, id)).toHaveCount(0);
  expect((await state(page)).referrals.find((r) => r.id === id)?.status).toBe(
    "COMPLETED",
  );
}

test("five-minute demo: reviewed referral, 8/7/5 plan, activation, funding and exports", async ({
  page,
}, info) => {
  const started = Date.now();
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  // Block public resources: model and map must work without runtime downloads.
  await page.route("**/*", (route) =>
    new URL(route.request().url()).hostname === "127.0.0.1"
      ? route.continue()
      : route.abort(),
  );
  await login(page, "planner");
  await expect(page.locator(".city-pin")).toHaveCount(8);
  await expect(page.locator(".pilot-map")).toHaveAttribute(
    "data-engine",
    /^(webgl|software)-3d$/,
  );
  expect((await state(page)).summary).toMatchObject({
    unresolved: 20,
    confirmed: 40,
    completed: 20,
  });
  await responsive(page);
  await page.screenshot({
    path: info.outputPath("network.png"),
    fullPage: true,
  });

  await switchRole(page, "operator-p03");
  await page
    .getByRole("button", {
      name: /^(Referral coordination|Receiving desk)$/,
      exact: true,
    })
    .click();
  await page
    .getByLabel("Service description", { exact: true })
    .fill("a routine visit with a family physician");
  await saved(
    page,
    page.getByRole("button", { name: "Suggest service category", exact: true }),
    "matching/services",
  );
  await saved(
    page,
    page.getByRole("button", {
      name: /General primary-care OPD · review suggestion/,
    }),
    "matching/reviews",
  );
  await expect(
    page.getByText("Human review recorded", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Patient reference", { exact: true })
    .fill("BROWSER-EAST");
  await page.getByLabel("Pilot zone", { exact: true }).selectOption("East");
  await page
    .getByLabel(
      "Authorized staff established non-emergency primary-care suitability",
      { exact: true },
    )
    .check();
  await saved(
    page,
    page.getByRole("button", { name: "Register request", exact: true }),
    "requests",
  );
  const east = await reserve(page, "BROWSER-EAST", "P04", true);
  await saved(
    page,
    referral(page, east.id).getByRole("button", {
      name: "Accept referral",
      exact: true,
    }),
    `referrals/${east.id}/partner-response`,
  );
  await saved(
    page,
    referral(page, east.id).getByRole("button", {
      name: "Record patient agreement",
      exact: true,
    }),
    `referrals/${east.id}/patient-agreement`,
  );
  await complete(page, east.id);
  await page.reload();
  expect(
    (await state(page)).requests.find((r) => r.reference === "BROWSER-EAST")
      ?.status,
  ).toBe("FULFILLED");

  await switchRole(page, "planner");
  await page
    .getByRole("button", { name: "Unresolved demand", exact: true })
    .click();
  expect(
    (await state(page)).summary?.zones.map((z) => [z.zone, z.count]),
  ).toEqual(
    expect.arrayContaining([
      ["South", 8],
      ["Central", 7],
      ["North", 5],
    ]),
  );
  await page
    .getByRole("button", { name: "Monthly planner", exact: true })
    .click();
  const plan: Plan = await saved(
    page,
    page.getByRole("button", {
      name: "Create snapshot & optimize",
      exact: true,
    }),
    "plans/optimize",
  );
  expect(plan).toMatchObject({
    additional: 20,
    baseline: 0,
    cost: 25000,
    subsidy_cost: 8000,
    solver_status: "OPTIMAL",
  });
  expect(plan.assignments.filter((a) => a.subsidy > 0)).toHaveLength(8);
  expect(plan.actions.map((a) => [a.offer_id, a.cost])).toEqual(
    expect.arrayContaining([
      ["QUOTA-7", 7000],
      ["MOBILE-5", 10000],
    ]),
  );
  await saved(
    page,
    page.getByRole("button", { name: "Approve plan", exact: true }),
    `plans/${plan.id}/approve`,
  );
  await page.reload();
  await page
    .getByRole("button", { name: "Monthly planner", exact: true })
    .click();
  await page.getByRole("button", { name: new RegExp(`^${plan.id} ·`) }).click();
  await expect(
    card(page, `Plan ${plan.id}`).getByText("approved", { exact: true }),
  ).toBeVisible();

  for (const account of ["operator-p02", "operator-p08"]) {
    await switchRole(page, account);
    await page
      .getByRole("button", { name: "Offers & activation", exact: true })
      .click();
    await page
      .getByRole("button", { name: new RegExp(`^${plan.id} ·`) })
      .click();
    await saved(
      page,
      page.getByRole("button", {
        name: "Confirm & activate offered resource",
        exact: true,
      }),
      `plans/${plan.id}/actions/`,
    );
    await expect(
      card(page, `Plan ${plan.id}`).locator(".plan-actions .badge"),
    ).toHaveText("active");
  }
  await responsive(page);

  await switchRole(page, "operator-p08");
  await page
    .getByRole("button", {
      name: /^(Referral coordination|Receiving desk)$/,
      exact: true,
    })
    .click();
  const bRow = page
    .getByRole("row")
    .filter({ has: page.getByText("B-01", { exact: true }) });
  await bRow.getByRole("button", { name: "Reprocess", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByLabel("Reason for this decision")
    .fill("Activated quota is available for this synthetic request");
  await saved(
    page,
    page.getByRole("dialog").getByRole("button", { name: "Save decision" }),
    "requests/B-01/reprocess",
  );
  const b = await reserve(page, "B-01", "P02");
  await saved(
    page,
    referral(page, b.id).getByRole("button", {
      name: "Record patient agreement",
      exact: true,
    }),
    `referrals/${b.id}/patient-agreement`,
  );
  await switchRole(page, "operator-p02");
  await page
    .getByRole("button", {
      name: /^(Referral coordination|Receiving desk)$/,
      exact: true,
    })
    .click();
  await saved(
    page,
    referral(page, b.id).getByRole("button", {
      name: "Accept referral",
      exact: true,
    }),
    `referrals/${b.id}/partner-response`,
  );
  await complete(page, b.id);

  // Approved-plan subsidy already carries planner authorization.
  await switchRole(page, "operator-p08");
  await page
    .getByRole("button", {
      name: /^(Referral coordination|Receiving desk)$/,
      exact: true,
    })
    .click();
  const a = await reserve(page, "A-01", "P01");
  expect(a.subsidy).toBe(1000);
  await saved(
    page,
    referral(page, a.id).getByRole("button", {
      name: "Accept referral",
      exact: true,
    }),
    `referrals/${a.id}/partner-response`,
  );
  await saved(
    page,
    referral(page, a.id).getByRole("button", {
      name: "Record patient agreement",
      exact: true,
    }),
    `referrals/${a.id}/patient-agreement`,
  );
  await expect(referral(page, a.id).locator(".badge")).toHaveText("confirmed");
  await complete(page, a.id);

  await switchRole(page, "planner");
  await page
    .getByRole("button", { name: "Monthly planner", exact: true })
    .click();
  await page.getByRole("button", { name: new RegExp(`^${plan.id} ·`) }).click();
  const persisted = await state(page);
  expect(persisted.summary).toMatchObject({
    unresolved: 18,
    confirmed: 43,
    completed: 23,
    projected_additional: 20,
    post_activation_confirmed: 2,
    post_activation_completed: 2,
  });
  await expect(
    card(page, "Projected versus recorded outcomes").locator(".funnel strong"),
  ).toHaveText(["20", "2", "2"]);
  for (const format of ["JSON", "CSV"]) {
    const downloadPromise = page.waitForEvent("download");
    await page
      .getByRole("button", { name: `${format} summary`, exact: true })
      .click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe(
      `sehat-grid-${plan.id}.${format.toLowerCase()}`,
    );
    const contents = await readFile((await download.path())!, "utf8");
    expect(contents).toContain("input_hash");
    expect(contents).toContain("Synthetic demo data");
    expect(contents).not.toContain("request_id");
    if (format === "JSON")
      expect(JSON.parse(contents).actual).toMatchObject({
        completed: 23,
        post_activation_completed: 2,
      });
    await download.saveAs(info.outputPath(`plan.${format.toLowerCase()}`));
  }
  await responsive(page);
  await page.screenshot({
    path: info.outputPath("outcomes.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Monthly outcomes", exact: true })
    .click();
  await expect(page.locator(".outcome-bars strong")).toHaveText([
    "20",
    "2",
    "2",
  ]);
  await page.screenshot({
    path: info.outputPath("monthly-delivery.png"),
    fullPage: true,
  });
  expect(failures).toEqual([]);
  const duration = Date.now() - started;
  expect(duration).toBeLessThan(300_000);
  await info.attach("demo-evidence", {
    body: JSON.stringify(
      {
        browser: await page.context().browser()!.version(),
        viewport: page.viewportSize(),
        duration_ms: duration,
        summary: persisted.summary,
        runtime_public_requests_blocked: true,
      },
      null,
      2,
    ),
    contentType: "application/json",
  });
});

test("independent subsidy requires planner funding authorization before completion", async ({
  page,
}) => {
  await login(page, "operator-p08");
  await page
    .getByRole("button", {
      name: /^(Referral coordination|Receiving desk)$/,
      exact: true,
    })
    .click();
  const a = await reserve(page, "A-01", "P01");
  await saved(
    page,
    referral(page, a.id).getByRole("button", {
      name: "Accept referral",
      exact: true,
    }),
    `referrals/${a.id}/partner-response`,
  );
  await saved(
    page,
    referral(page, a.id).getByRole("button", {
      name: "Record patient agreement",
      exact: true,
    }),
    `referrals/${a.id}/patient-agreement`,
  );
  await expect(referral(page, a.id).locator(".badge")).toHaveText(
    "awaiting confirmations",
  );
  await switchRole(page, "planner");
  await page
    .getByRole("button", { name: "Funding approvals", exact: true })
    .click();
  await saved(
    page,
    referral(page, a.id).getByRole("button", {
      name: "Authorize funding",
      exact: true,
    }),
    `referrals/${a.id}/funding-approval`,
  );
  await switchRole(page, "operator-p08");
  await page
    .getByRole("button", {
      name: /^(Referral coordination|Receiving desk)$/,
      exact: true,
    })
    .click();
  await complete(page, a.id);
  await responsive(page);
});

test("ranking integration, stale-version recovery and operator permission", async ({
  page,
  context,
}) => {
  await login(page, "onboarder-p04");
  const settings = card(page, "Own provider settings")
    .locator("details")
    .first();
  await settings
    .getByLabel("Pilot zone", { exact: true })
    .selectOption("Central");
  await saved(
    page,
    settings.getByRole("button", { name: "Update profile", exact: true }),
    "facilities/P04",
  );
  await switchRole(page, "operator-p03");
  await page
    .getByRole("button", {
      name: /^(Referral coordination|Receiving desk)$/,
      exact: true,
    })
    .click();
  await saved(
    page,
    page.getByRole("button", { name: "Suggest service category", exact: true }),
    "matching/services",
  );
  await saved(
    page,
    page.getByRole("button", {
      name: /General primary-care OPD · review suggestion/,
    }),
    "matching/reviews",
  );
  await page
    .getByLabel("Patient reference", { exact: true })
    .fill("RANKING-EAST");
  await page.getByLabel("Pilot zone", { exact: true }).selectOption("East");
  await page
    .getByLabel(
      "Authorized staff established non-emergency primary-care suitability",
      { exact: true },
    )
    .check();
  await saved(
    page,
    page.getByRole("button", { name: "Register request", exact: true }),
    "requests",
  );
  const row = page
    .getByRole("row")
    .filter({ has: page.getByText("RANKING-EAST", { exact: true }) });
  await row
    .getByRole("button", { name: "Find providers", exact: true })
    .click();
  await expect(
    page.locator(".recommendation").first().locator("strong"),
  ).toHaveText("Kulsum International Hospital");
  await switchRole(page, "planner");
  await page
    .getByRole("button", { name: "Funding approvals", exact: true })
    .click();
  const ranking = card(page, "Referral ranking policy");
  await ranking
    .getByLabel("Preferred order")
    .selectOption("available,subsidy,same_zone");
  await ranking
    .getByLabel("Reason for ranking change")
    .fill("Prefer larger eligible quota for the synthetic demo");
  await saved(
    page,
    ranking.getByRole("button", { name: "Save referral ranking" }),
    "referral-ranking",
  );
  await expect(ranking.getByText(/referral-ranking-v2/)).toBeVisible();
  const other = await context.newPage();
  await login(other, "planner");
  await other
    .getByRole("button", { name: "Funding approvals", exact: true })
    .click();
  await other
    .getByLabel("Preferred order")
    .selectOption("available,same_zone,subsidy");
  await other
    .getByLabel("Reason for ranking change")
    .fill("Another planner changes the order concurrently");
  await saved(
    other,
    other.getByRole("button", { name: "Save referral ranking" }),
    "referral-ranking",
  );
  await ranking
    .getByLabel("Reason for ranking change")
    .fill("Stale write must be rejected and refreshed");
  await ranking.getByRole("button", { name: "Save referral ranking" }).click();
  await expect(page.locator('.error[role="alert"]')).toContainText(
    "Current inputs have been refreshed",
  );
  await expect(ranking.getByText(/referral-ranking-v3/)).toBeVisible();
  await expect(ranking.getByLabel("Preferred order")).toHaveValue(
    "available,same_zone,subsidy",
  );
  await other.close();
  await switchRole(page, "operator-p03");
  await expect(
    page.getByRole("button", { name: "Funding approvals", exact: true }),
  ).toHaveCount(0);
  const status = await page.evaluate(
    async () =>
      (
        await fetch("/api/v1/referral-ranking", {
          headers: {
            Authorization: `Bearer ${sessionStorage.getItem("sehat-token")}`,
          },
        })
      ).status,
  );
  expect(status).toBe(403);
  await page
    .getByRole("button", {
      name: /^(Referral coordination|Receiving desk)$/,
      exact: true,
    })
    .click();
  await row
    .getByRole("button", { name: "Find providers", exact: true })
    .click();
  await expect(
    page.locator(".recommendation").first().locator("strong"),
  ).toHaveText("Kulsum International Hospital");
  await expect(
    page
      .locator(".recommendation")
      .first()
      .getByText(/referral-ranking-v3/),
  ).toBeVisible();
  await expect(card(page, "Referral ranking policy")).toHaveCount(0);
  await responsive(page);
});

test("empty states, failed login, API outage recovery and expired session", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill("planner");
  await page.getByLabel("Password", { exact: true }).fill("incorrect-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator('.error[role="alert"]')).toHaveText(
    "Incorrect username or password",
  );
  await login(page, "operator-p02");
  await page
    .getByRole("button", { name: "Matching & review", exact: true })
    .click();
  await expect(
    page.getByText("No human reviews recorded yet.", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name: /^(Referral coordination|Receiving desk)$/,
      exact: true,
    })
    .click();
  await expect(
    page.getByText("No referrals need action in this view.", { exact: true }),
  ).toBeVisible();
  await page.route("**/api/v1/state*", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Backend temporarily unavailable" }),
    }),
  );
  await page.reload();
  await expect(page.locator('.error[role="alert"]')).toHaveText(
    "Backend temporarily unavailable",
  );
  await expect(
    page.getByRole("button", { name: "Retry workspace", exact: true }),
  ).toBeVisible();
  await page.unroute("**/api/v1/state*");
  await page
    .getByRole("button", { name: "Retry workspace", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Sign out", exact: true }),
  ).toBeVisible();
  await switchRole(page, "onboarder-p08");
  await page.route("**/api/v1/facilities/P08/capacity/**", (route) =>
    route.continue({
      url: route
        .request()
        .url()
        .replace("/facilities/P08/", "/facilities/P01/"),
    }),
  );
  await page
    .getByRole("button", { name: "Update dated quota", exact: true })
    .click();
  await expect(page.locator('.error[role="alert"]')).toContainText(
    "Hospital setup permission for this facility is required",
  );
  await page.unroute("**/api/v1/facilities/P08/capacity/**");
  await page.evaluate(() =>
    sessionStorage.setItem("sehat-token", "expired-invalid-token"),
  );
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
  await responsive(page);
});

test("resource rejection requires a reason and updates persisted totals", async ({
  page,
}) => {
  await login(page, "planner");
  await page
    .getByRole("button", { name: "Monthly planner", exact: true })
    .click();
  const plan = await saved(
    page,
    page.getByRole("button", {
      name: "Create snapshot & optimize",
      exact: true,
    }),
    "plans/optimize",
  );
  await saved(
    page,
    page.getByRole("button", { name: "Approve plan", exact: true }),
    `plans/${plan.id}/approve`,
  );
  await switchRole(page, "operator-p08");
  await page
    .getByRole("button", { name: "Offers & activation", exact: true })
    .click();
  await page.getByRole("button", { name: new RegExp(`^${plan.id} ·`) }).click();
  await page
    .getByRole("button", { name: "Reject offered resource", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByLabel("Reason for this decision")
    .fill("Synthetic mobile unit unavailable for this date");
  await saved(
    page,
    page.getByRole("dialog").getByRole("button", { name: "Save decision" }),
    `plans/${plan.id}/actions/`,
  );
  await switchRole(page, "planner");
  await page
    .getByRole("button", { name: "Monthly planner", exact: true })
    .click();
  await page.getByRole("button", { name: new RegExp(`^${plan.id} ·`) }).click();
  expect((await state(page)).plans.find((p) => p.id === plan.id)).toMatchObject(
    { additional: 15, cost: 15000, unresolved_remaining: 5 },
  );
  await expect(
    card(page, `Plan ${plan.id}`).getByText("rejected", { exact: true }),
  ).toBeVisible();
  execFileSync("docker", [...compose, "restart", "api"], {
    cwd: repo,
    stdio: "pipe",
    timeout: 60_000,
  });
  await expect
    .poll(
      async () => {
        try {
          return (await page.request.get("/health", { timeout: 2000 })).ok();
        } catch {
          return false;
        }
      },
      { timeout: 60_000, intervals: [1000] },
    )
    .toBeTruthy();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Sign out", exact: true }),
  ).toBeVisible();
  expect((await state(page)).plans.find((p) => p.id === plan.id)).toMatchObject(
    { additional: 15, cost: 15000, unresolved_remaining: 5 },
  );
  await responsive(page);
});

test("software 3D map preserves colors, interaction and keyboard selection without WebGL", async ({
  page,
}, info) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
      ...args: Parameters<typeof original>
    ) {
      if (String(args[0]).includes("webgl")) return null;
      return original.apply(this, args);
    } as typeof original;
  });
  await login(page, "planner");
  const map = page.getByLabel("Interactive 3D Islamabad hospital map", {
    exact: true,
  });
  await expect(map).toBeVisible();
  await expect(map).toHaveAttribute("data-engine", "software-3d");
  const p02 = map.getByRole("button", {
    name: "Select Pakistan Institute of Medical Sciences (PIMS)",
    exact: true,
  });
  await expect(p02).toHaveCSS("border-top-color", "rgb(223, 115, 123)");
  await p02.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.locator(".city-detail").getByRole("heading", {
      name: "Pakistan Institute of Medical Sciences (PIMS)",
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Rotate city", exact: true }).click();
  await page.getByRole("button", { name: "Zoom in", exact: true }).click();
  await page
    .getByRole("button", { name: "Reset map view", exact: true })
    .click();
  await responsive(page);
  await page.screenshot({
    path: info.outputPath("offline-fallback.png"),
    fullPage: true,
  });
});

test("manual draft revision validates reason, survives reload, approves and exports", async ({
  page,
}, info) => {
  await login(page, "planner");
  await page
    .getByRole("button", { name: "Monthly planner", exact: true })
    .click();
  const plan = await saved(
    page,
    page.getByRole("button", {
      name: "Create snapshot & optimize",
      exact: true,
    }),
    "plans/optimize",
  );
  await page
    .getByRole("button", { name: "Revise draft with reason", exact: true })
    .click();
  const editor = page.getByRole("dialog");
  await expect(
    editor.getByLabel("Resource for A-01", { exact: true }),
  ).toBeVisible();
  for (const id of [
    ...Array.from({ length: 7 }, (_, i) => `B-0${i + 1}`),
    ...Array.from({ length: 5 }, (_, i) => `C-0${i + 1}`),
  ]) {
    await editor
      .getByLabel(`Resource for ${id}`, { exact: true })
      .selectOption("");
  }
  await editor.getByLabel("Reason for draft revision").fill("   ");
  await editor
    .getByRole("button", { name: "Save draft revision", exact: true })
    .click();
  await expect(editor.locator('.error[role="alert"]')).toBeVisible();
  await expect(
    editor.getByLabel("Resource for B-01", { exact: true }),
  ).toHaveValue("");
  await editor
    .getByLabel("Reason for draft revision")
    .fill("Run the initial pilot with the eight subsidy-supported requests");
  const revised = await saved(
    page,
    editor.getByRole("button", { name: "Save draft revision", exact: true }),
    `plans/${plan.id}/revise`,
  );
  expect(revised).toMatchObject({
    version: 2,
    decision_source: "HUMAN_REVISION",
    additional: 8,
    cost: 8000,
    actions: [],
    unresolved_remaining: 12,
  });
  expect(revised.original_solver_result).toMatchObject({
    coverage: 20,
    cost: 25000,
    status: "OPTIMAL",
  });
  await expect(editor).toHaveCount(0);
  await page.reload();
  await page
    .getByRole("button", { name: "Monthly planner", exact: true })
    .click();
  await page.getByRole("button", { name: new RegExp(`^${plan.id} ·`) }).click();
  await expect(
    card(page, `Plan ${plan.id}`).getByText("Original solver result", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    card(page, `Plan ${plan.id}`).getByText(/Human revision · version 2/),
  ).toBeVisible();
  await responsive(page);
  await page.screenshot({
    path: info.outputPath("human-revision.png"),
    fullPage: true,
  });
  await saved(
    page,
    page.getByRole("button", { name: "Approve plan", exact: true }),
    `plans/${plan.id}/approve`,
  );
  for (const format of ["JSON", "CSV"]) {
    const downloadPromise = page.waitForEvent("download");
    await page
      .getByRole("button", { name: `${format} summary`, exact: true })
      .click();
    const download = await downloadPromise;
    const contents = await readFile((await download.path())!, "utf8");
    expect(contents).toContain("HUMAN_REVISION");
    expect(contents).not.toContain("request_id");
    if (format === "JSON") {
      expect(JSON.parse(contents)).toMatchObject({
        cost: 8000,
        additional: 8,
        decision_source: "HUMAN_REVISION",
        original_solver_result: { projected: 20, additional: 20, cost: 25000 },
      });
    }
  }
});

test("concurrent draft edits preserve choices and require explicit reload", async ({
  page,
  context,
}) => {
  await login(page, "planner");
  await page
    .getByRole("button", { name: "Monthly planner", exact: true })
    .click();
  const plan = await saved(
    page,
    page.getByRole("button", {
      name: "Create snapshot & optimize",
      exact: true,
    }),
    "plans/optimize",
  );
  await page
    .getByRole("button", { name: "Revise draft with reason", exact: true })
    .click();
  await expect(
    page.getByRole("dialog").getByLabel("Resource for A-01", { exact: true }),
  ).toBeVisible();
  const other = await context.newPage();
  await login(other, "planner");
  await other
    .getByRole("button", { name: "Monthly planner", exact: true })
    .click();
  await other
    .getByRole("button", { name: new RegExp(`^${plan.id} ·`) })
    .click();
  await other
    .getByRole("button", { name: "Revise draft with reason", exact: true })
    .click();
  await other
    .getByRole("dialog")
    .getByLabel("Reason for draft revision")
    .fill("Another planner validates these choices first");
  await saved(
    other,
    other
      .getByRole("dialog")
      .getByRole("button", { name: "Save draft revision", exact: true }),
    `plans/${plan.id}/revise`,
  );
  const editor = page.getByRole("dialog");
  await editor
    .getByLabel("Resource for B-01", { exact: true })
    .selectOption("");
  await editor
    .getByLabel("Reason for draft revision")
    .fill("This outdated edit must be rejected");
  await editor
    .getByRole("button", { name: "Save draft revision", exact: true })
    .click();
  await expect(editor.locator('.error[role="alert"]')).toContainText(
    "Draft was edited",
  );
  await expect(
    editor.getByLabel("Resource for B-01", { exact: true }),
  ).toHaveValue("");
  await expect(
    editor.getByRole("button", { name: "Save draft revision", exact: true }),
  ).toBeDisabled();
  await editor
    .getByRole("button", { name: "Reload current draft choices", exact: true })
    .click();
  await expect(editor.getByText(/Draft version 2/)).toBeVisible();
  await expect(
    editor.getByLabel("Resource for B-01", { exact: true }),
  ).toHaveValue("QUOTA-7");
  await editor
    .getByRole("button", { name: "Close dialog", exact: true })
    .click();
  await page.getByRole("button", { name: "Approve plan", exact: true }).click();
  await expect(page.locator('.error[role="alert"]')).toContainText(
    "Current inputs have been refreshed",
  );
  expect((await state(page)).plans.find((p) => p.id === plan.id)?.status).toBe(
    "DRAFT",
  );
  await responsive(page);
  await other.close();
});

test("a proposed attempt can be cancelled without holding quota or budget", async ({
  page,
}) => {
  await login(page, "operator-p08");
  const before = await state(page);
  await page
    .getByRole("button", {
      name: /^(Referral coordination|Receiving desk)$/,
      exact: true,
    })
    .click();
  await page
    .getByRole("row")
    .filter({ has: page.getByText("A-01", { exact: true }) })
    .getByRole("button", { name: "Find providers", exact: true })
    .click();
  const proposal = await saved(
    page,
    page.getByRole("button", { name: "Save referral proposal", exact: true }),
    "referrals/proposals",
  );
  await referral(page, proposal.id)
    .getByRole("button", { name: "Cancel proposal", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByLabel("Reason for this decision")
    .fill("Sender chose to reconsider the proposed destination");
  await saved(
    page,
    page.getByRole("dialog").getByRole("button", { name: "Save decision" }),
    `referrals/${proposal.id}/cancel`,
  );
  const after = await state(page);
  expect(after.referrals.find((r) => r.id === proposal.id)?.status).toBe(
    "CANCELLED",
  );
  expect(after.facilities.map((f) => f.capacities)).toEqual(
    before.facilities.map((f) => f.capacities),
  );
  await switchRole(page, "planner");
  expect((await state(page)).summary?.budget).toMatchObject({
    HELD: 0,
    COMMITTED: 0,
    SETTLED: 0,
    remaining: 25000,
  });
});
