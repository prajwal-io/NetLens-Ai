import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on('pageerror', error => errors.push(error.message));
try {
  await page.goto('http://127.0.0.1:5175/traffic-analyzer');
  await page.getByLabel('Traffic CSV file').setInputFiles('../data/qa/real-heldout.csv');
  await page.getByRole('button', { name: 'Validate CSV', exact: true }).click();
  await page.getByText('1,000 rows validated').waitFor({ timeout: 30000 });
  const inference = page.waitForResponse(response => response.url().endsWith('/traffic/analyze'));
  await page.getByRole('button', { name: /Analyze flows/ }).click();
  const result = await (await inference).json();
  await page.getByRole('heading', { name: 'Model analysis', exact: true }).waitFor({ timeout: 60000 });
  const summary = await page.locator('.analysis-summary').innerText();
  for (const name of ['Command Center', 'Network Pulse', 'Threat Investigation', 'Reports']) {
    await page.locator('.desktop-navigation').getByRole('link', { name, exact: true }).click();
    await page.getByRole('heading', { name: `${name}: uploaded analysis`, exact: true }).waitFor();
    assert.match(await page.locator('.analysis-summary').innerText(), /1,000/);
    assert.match(await page.locator('main').innerText(), /netsight-rf-unsw-v3/);
    assert.ok((await page.locator('main').innerText()).includes(result.analysis_id));
    assert.ok((await page.locator('.analysis-summary').innerText()).includes(String(result.counts.normal)));
    assert.ok((await page.locator('.analysis-summary').innerText()).includes(String(result.counts.malicious)));
    await page.getByRole('button', { name: 'Next', exact: true }).click();
    await page.getByRole('button', { name: 'Previous', exact: true }).click();
    await page.getByLabel('Classification', { exact: true }).selectOption('malicious');
    await page.getByLabel('Classification', { exact: true }).selectOption('all');
  }
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export classification CSV' }).click();
  const file = await download;
  assert.match(file.suggestedFilename(), /netsight-.*\.csv/);
  const exported = (await readFile(await file.path(), 'utf8')).trim().split(/\r?\n/).slice(1);
  assert.equal(exported.length, result.total_flows);
  assert.deepEqual(exported.map(line => line.split(',')[1]), result.predictions.map(row => row.label));
  await page.screenshot({ path: '../docs/linked-analysis-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: '../docs/linked-analysis-mobile.png', fullPage: true });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ passed: true, source: 'Official held-out UNSW-NB15 CSV, 1000 real benchmark rows', summary, checks: ['real upload', 'schema validation', 'actual model inference', 'four linked views', 'pagination/filter', 'CSV export', 'mobile overflow', 'no page errors'] }, null, 2));
} catch (error) { console.error(await page.locator('main').innerText()); throw error; }
finally { await browser.close(); }
