import { test, expect } from "@playwright/test";

test("guided fills, FIFO, symbol isolation and saved replay", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByText("Local service connected")).toBeVisible();
  await expect(
    page.getByText("Synthetic simulation", { exact: true }),
  ).toBeVisible();
  for (let i = 0; i < 4; i++)
    await page
      .getByRole("button", { name: "Single step", exact: true })
      .click();
  await expect(page.getByRole("status")).toContainText(
    "cheapest seller fills 100",
  );
  await expect(
    page.getByRole("row").filter({ hasText: "seller-low → buyer-130" }),
  ).toContainText("$101.00");
  await expect(
    page.getByRole("row").filter({ hasText: "seller-high → buyer-130" }),
  ).toContainText("30");
  for (let i = 0; i < 2; i++)
    await page
      .getByRole("button", { name: "Single step", exact: true })
      .click();
  await expect(page.getByRole("status")).toContainText("older 70 shares");
  await expect(
    page.getByRole("row").filter({ hasText: "seller-later → buyer-fifo" }),
  ).toContainText("10");
  for (let i = 0; i < 2; i++)
    await page
      .getByRole("button", { name: "Single step", exact: true })
      .click();
  await expect(page.getByRole("status")).toContainText("cannot match");
  await expect(
    page.getByRole("row").filter({ hasText: "isolated-bid" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "DEMO SIM" }).click();
  await page.screenshot({
    path: "../docs/assets/exchange-lab.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Replay saved session" }).click();
  await expect(page.getByRole("status")).toContainText(
    "identical final state and trades",
  );
  await page.getByRole("button", { name: "Single step", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("event 1/");
  await page.getByRole("button", { name: "Play", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("event 2/");
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  const paused = await page.getByRole("status").textContent();
  await page.waitForTimeout(1200);
  await expect(page.getByRole("status")).toHaveText(paused!);
  await page.getByRole("button", { name: "Return to current book" }).click();
  await expect(
    page.getByRole("row").filter({ hasText: "seller-later → buyer-fifo" }),
  ).toBeVisible();
});

test("submit, replace, cancel, fill and reset", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Reset DEMO" }).click();
  await expect(page.getByRole("status")).toContainText("RESET accepted");
  await page.getByLabel("Order ID", { exact: true }).fill("browser-seller");
  await page.getByLabel("Side", { exact: true }).selectOption("SELL");
  await page.getByLabel("Shares", { exact: true }).fill("100");
  await page.getByLabel("Limit price ($)", { exact: true }).fill("101.00");
  await page.getByRole("button", { name: "Submit sell · DEMO" }).click();
  await expect(
    page.getByRole("row").filter({ hasText: "browser-seller" }),
  ).toContainText("100");
  await page.getByLabel("Shares", { exact: true }).fill("90");
  await page
    .getByRole("button", { name: "Replace browser-seller", exact: true })
    .click();
  await expect(
    page.getByRole("row").filter({ hasText: "browser-seller" }),
  ).toContainText("90");
  await page.getByLabel("Order ID", { exact: true }).fill("browser-buyer");
  await page.getByLabel("Side", { exact: true }).selectOption("BUY");
  await page.getByLabel("Shares", { exact: true }).fill("40");
  const started = Date.now();
  await page.getByRole("button", { name: "Submit buy · DEMO" }).click();
  await expect(
    page.getByRole("row").filter({ hasText: "browser-seller → browser-buyer" }),
  ).toContainText("40");
  console.log(`browser click-to-visible fill: ${Date.now() - started} ms`);
  await page
    .getByRole("button", { name: "Cancel browser-seller", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Cancel browser-seller", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Reset DEMO" }).click();
  await expect(
    page.getByText("No trades yet. Step through the scenario to see a fill."),
  ).toBeVisible();
});

test("SSE cursor reconnect returns ordered commits and coherent snapshot", async ({
  request,
  page,
}) => {
  const before = (await (await request.get("/api/snapshot")).json()).seq;
  for (let i = 0; i < 3; i++)
    await request.post("/api/commands", {
      data: { kind: "RESET", symbol: "NVDA", request_id: crypto.randomUUID() },
    });
  await page.goto("/");
  const frames = await page.evaluate(async (cursor) => {
    const abort = new AbortController();
    const r = await fetch(`/api/events?cursor=0`, {
      headers: { "Last-Event-ID": String(cursor) },
      signal: abort.signal,
    });
    const reader = r.body!.getReader();
    let text = "";
    while (!text.includes("event: snapshot")) {
      const part = await reader.read();
      text += new TextDecoder().decode(part.value);
    }
    abort.abort();
    return text;
  }, before);
  const data = frames
    .split("\n\n")
    .filter((x) => x.includes("event: exchange"))
    .map((x) => JSON.parse(x.split("data: ")[1]));
  expect(data.map((x) => x.seq)).toEqual([before + 1, before + 2, before + 3]);
  expect(frames).toContain(`id: ${before + 3}\nevent: snapshot`);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Submit buy · DEMO" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});
