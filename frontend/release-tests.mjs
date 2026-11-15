import { chromium } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import assert from 'node:assert/strict';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
const base = process.env.NETSIGHT_TEST_URL || 'http://127.0.0.1:5176';
const executablePath = process.env.CHROME_PATH || (existsSync('C:/Program Files/Google/Chrome/Application/chrome.exe') ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : undefined);
const browser = await chromium.launch({ executablePath, headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
const page = await context.newPage();
const errors = [], checks = [], scans = [], created = [], external = [];
await page.route('**/*', route => { const url = new URL(route.request().url()); if (url.protocol.startsWith('http') && !['127.0.0.1', 'localhost'].includes(url.hostname)) { external.push(url.href); return route.abort(); } return route.continue(); });
page.on('pageerror', error => errors.push(error.message));
try {
  const source = await readFile('../backend/data/replays/normal-benchmark.csv', 'utf8');
  // Real benchmark features + documentation-only IPs/times to test optional topology.
  // These extra context fields are test fixtures, not captured network metadata.
  const lines = source.trim().split(/\r?\n/);
  const context = lines.map((line, i) => i === 0 ? `${line},source_ip,destination_ip,timestamp` : `${line},192.0.2.${i % 4 + 1},198.51.100.${i % 3 + 1},2026-11-09T10:00:${String(i % 60).padStart(2, '0')}Z`).join('\n');
  await mkdir('../data/qa', { recursive: true });
  await writeFile('../data/qa/release-topology.csv', context);
  await page.goto(`${base}/traffic-analyzer`);
  await page.getByLabel('Traffic CSV file').setInputFiles('../data/qa/release-topology.csv');
  await page.getByRole('button', { name: 'Validate CSV', exact: true }).click();
  await page.getByText('100 rows validated', { exact: false }).waitFor();
  const inference = page.waitForResponse(r => r.url().endsWith('/traffic/analyze'));
  await page.getByRole('button', { name: /Analyze flows/ }).click();
  const result = await (await inference).json(); created.push(result.analysis_id);
  await page.getByRole('heading', { name: 'Model analysis', exact: true }).waitFor();
  assert.equal(result.total_flows, 100);
  checks.push('Real benchmark features: validation -> active model -> SQLite');
  for (const [path, name] of [['command-center','Command Center'], ['network-pulse','Network Pulse'], ['threat-investigation','Threat Investigation'], ['reports','Reports']]) {
    await page.goto(`${base}/${path}`);
    await page.getByRole('heading', { name: `${name}: uploaded analysis`, exact: true }).waitFor();
    assert.ok((await page.locator('main').innerText()).includes(result.analysis_id));
    if (path === 'network-pulse') {
      await page.getByLabel('Inspect device', { exact: false }).selectOption('192.0.2.1');
      assert.ok((await page.locator('.connection-list').innerText()).includes('192.0.2.1'));
    }
    if (path === 'threat-investigation') {
      await page.getByRole('button', { name: 'Next', exact: true }).click();
      await page.locator('tbody tr').first().locator('summary').click();
      await page.locator('tbody tr').first().locator('dl').waitFor();
    }
  }
  checks.push('Reload persistence; four linked views; topology controls; full flow details');
  for (const [name, extension] of [['Export classification CSV','csv'], ['Download PDF report','pdf']]) {
    const pending = page.waitForEvent('download');
    await page.getByRole('button', { name }).click();
    const download = await pending, bytes = await readFile(await download.path());
    if (extension === 'pdf') assert.equal(bytes.subarray(0,5).toString(), '%PDF-');
    else assert.equal(bytes.toString('utf8').trim().split(/\r?\n/).length, 101);
  }
  checks.push('Server CSV and PDF downloads');
  await page.goto(`${base}/network-pulse`);
  await page.getByRole('button', { name: 'Analyze historical replay' }).waitFor();
  const response = page.waitForResponse(r => /replays\/.*\/analyze$/.test(r.url()));
  await page.getByRole('button', { name: 'Analyze historical replay' }).click();
  const replay = await (await response).json(); created.push(replay.analysis_id);
  await page.getByRole('heading', { name: 'Network Pulse: historical replay', exact: true }).waitFor();
  assert.ok(await page.getByText('No device topology is available', { exact: false }).isVisible());
  await page.getByRole('button', { name: 'Play replay', exact: true }).click();
  await page.waitForTimeout(1200);
  await page.getByRole('button', { name: 'Pause replay', exact: true }).click();
  assert.ok(Number(await page.getByLabel('Replay position').inputValue()) >= 1);
  const paused = await page.getByLabel('Replay position').inputValue();
  await page.waitForTimeout(600); assert.equal(await page.getByLabel('Replay position').inputValue(), paused);
  await page.getByRole('button', { name: 'Restart replay' }).click();
  assert.equal(await page.getByLabel('Replay position').inputValue(), '0');
  await page.getByLabel('Playback speed').selectOption('4');
  await page.getByLabel('Replay position').fill('100');
  checks.push('Real replay inference; play/pause/restart/speed/seek; no invented topology');
  for (const route of ['', 'command-center', 'network-pulse', 'traffic-analyzer', 'threat-investigation', 'model-lab', 'reports']) {
    await page.goto(`${base}/${route}`);
    await page.locator('main h1').waitFor();
    await page.waitForTimeout(800);
    const audit = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
    scans.push({ route: route || 'landing', violations: audit.violations.map(item => ({ id: item.id, impact: item.impact, nodes: item.nodes.map(node => node.target) })) });
    for (const width of [390,768,1440]) {
      await page.setViewportSize({ width, height: 900 });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, `${route} overflow at ${width}`);
    }
  }
  await mkdir('../docs/release-evidence', { recursive: true });
  await page.goto(`${base}/reports`);
  await page.getByRole('heading', { name: 'Reports: historical replay' }).waitFor();
  await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(300);
  await page.screenshot({ path: '../docs/release-evidence/reports-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: '../docs/release-evidence/reports-mobile.png', fullPage: true });
  await page.goto(`${base}/network-pulse`);
  await page.getByRole('heading', { name: 'Network Pulse: historical replay' }).waitFor();
  await page.screenshot({ path: '../docs/release-evidence/replay-mobile.png', fullPage: true });
  await page.context().setOffline(true);
  await page.locator('.saved-history summary').click();
  await page.getByRole('button', { name: 'Refresh history' }).click();
  await page.locator('.saved-history [role="alert"]').waitFor();
  await page.context().setOffline(false);
  await page.getByRole('button', { name: 'Refresh history' }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('.mobile-navigation summary').click();
  await page.locator('.mobile-navigation').getByRole('link', { name: 'Command Center', exact: true }).click();
  await page.getByRole('heading', { name: 'Command Center: historical replay' }).waitFor();
  await page.reload(); await page.keyboard.press('Tab');
  assert.ok(await page.getByRole('link', { name: 'Skip to content' }).evaluate(element => document.activeElement === element));
  await page.keyboard.press('Enter');
  assert.equal(await page.locator('main').evaluate(element => document.activeElement === element), true);
  assert.deepEqual(external, []);
  checks.push('Keyboard skip link, mobile menu navigation, no external network dependencies');
  checks.push('Seven routes at 390/768/1440; reduced motion; offline history error/retry; axe accessibility scans');
  assert.deepEqual(errors, []);
  await writeFile('../docs/release-evidence/browser-results.json', JSON.stringify({ checks, scans, errors }, null, 2));
  const violations = scans.flatMap(scan => scan.violations.map(item => ({ route: scan.route, ...item })));
  console.log(JSON.stringify({ checks, violations, pageErrors: errors }, null, 2));
  assert.equal(violations.length, 0, 'Accessibility violations must be fixed');
} finally {
  for (const id of created) await page.request.delete(`${base}/api/v1/analyses/${id}`).catch(() => {});
  await browser.close();
}
