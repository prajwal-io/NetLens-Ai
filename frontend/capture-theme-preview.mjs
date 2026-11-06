import { chromium } from '@playwright/test';

const base = process.env.AUDIT_URL ?? 'http://127.0.0.1:4177';
const browser = await chromium.launch({
  executablePath: process.env.BROWSER_EXECUTABLE ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe',
});
const errors = [];

async function capture(path, width, height, output, waitForBackend = false) {
  const page = await browser.newPage({ viewport: { width, height } });
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(`${base}${path}`, { waitUntil: 'networkidle' });
  if (waitForBackend) await page.getByText('Backend connected', { exact: true }).waitFor();
  await page.waitForTimeout(800);
  await page.screenshot({ path: `../docs/${output}`, fullPage: true });
  const rain = await page.locator('.rain-column').evaluateAll(columns => columns.map(column => ({
    display: getComputedStyle(column).display,
    opacity: Number(getComputedStyle(column).opacity),
    animation: getComputedStyle(column).animationName,
  })));
  console.log(`${path} at ${width}px: ${rain.filter(item => item.display !== 'none').length} rain streams visible`);
  await page.close();
}

try {
  await capture('/', 1440, 1000, 'theme-landing.png');
  await capture('/command-center', 1440, 1000, 'theme-dashboard.png', true);
  await capture('/command-center', 390, 844, 'theme-mobile.png', true);
  if (errors.length) throw new Error(`Browser errors: ${errors.join('; ')}`);
} finally {
  await browser.close();
}
