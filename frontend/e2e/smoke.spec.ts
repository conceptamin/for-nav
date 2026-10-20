import { expect, test } from '@playwright/test';

const pages = [
  { path: '/driver/vehicle-secret-7', heading: '운전자 안내', param: 'vehicle-secret-7' },
  { path: '/control', heading: '관제' },
  { path: '/demo', heading: '시연 관리' },
  { path: '/runs/run-secret-42', heading: '실행 결과', param: 'run-secret-42' },
  { path: '/no-such-page', heading: '페이지를 찾을 수 없음' },
];

for (const { path, heading, param } of pages) {
  test(`${path}: 제목·landmark·가로 스크롤·키보드 포커스`, async ({ page, baseURL }) => {
    const external: string[] = [];
    page.on('request', (request) => {
      if (new URL(request.url()).origin !== new URL(baseURL!).origin) external.push(request.url());
    });

    await page.goto(path);
    const h1 = page.getByRole('heading', { level: 1 });
    await expect(h1).toHaveText(heading);
    await expect(h1).toHaveCount(1);
    await expect(page).toHaveTitle(`${heading} · YardPilot`);
    await expect(page.getByRole('main')).toContainText(heading);

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, '가로 스크롤 없음').toBeLessThanOrEqual(0);

    if (param) {
      await expect(page.locator('body')).not.toContainText(param);
      expect(await page.title()).not.toContain(param);
    }

    await page.keyboard.press('Tab');
    const skipLink = page.getByRole('link', { name: '본문 바로가기' });
    await expect(skipLink).toBeFocused();
    await expect(skipLink).toBeInViewport({ ratio: 1 });
    const outline = await skipLink.evaluate((el) => {
      const style = getComputedStyle(el);
      return { style: style.outlineStyle, width: parseFloat(style.outlineWidth) };
    });
    expect(outline.style, '포커스 표시').not.toBe('none');
    expect(outline.width, '포커스 표시 두께').toBeGreaterThanOrEqual(2);

    await page.keyboard.press('Enter');
    await expect(page.getByRole('main')).toBeFocused();

    expect(external, '외부 origin 요청 없음').toEqual([]);
  });
}
