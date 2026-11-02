import { expect, test } from "@playwright/test";

test("renders the tunnel manager and opens configuration", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("/");
  await expect(page.getByText("WikiTunnel", { exact: true })).toBeVisible();
  await expect(page.locator("h1").first()).toBeVisible();
  await expect(page.getByText("PostgreSQL Tunnel").first()).toBeVisible();
  await expect(page.getByText("完整链路检查")).toBeVisible();
  await expect(page.getByText("实时日志")).toBeVisible();

  await page.getByRole("button", { name: "设置" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("编辑隧道")).toBeVisible();
  await expect(dialog.locator("input").nth(1)).toHaveValue("root@remote.example.com");
  await expect(dialog.locator("input").nth(5)).toHaveValue("15432");
  await dialog.getByRole("button", { name: "关闭" }).click();
  await expect(dialog).toBeHidden();

  expect(pageErrors).toEqual([]);
});

test("shows the remote port safety dialog", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "清理端口" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("检查远端端口占用")).toBeVisible();
  await expect(dialog.getByText("只处理当前隧道、当前监听端口的单一 sshd 会话。")).toBeVisible();
  await dialog.getByRole("button", { name: "取消" }).click();
});

