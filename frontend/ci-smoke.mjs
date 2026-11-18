import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';
import { chromium } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('.', import.meta.url));
const vite = fileURLToPath(new URL('./node_modules/vite/bin/vite.js', import.meta.url));
const base = 'http://127.0.0.1:4187';
const server = spawn(process.execPath, [vite, '--configLoader', 'runner', '--host', '127.0.0.1', '--port', '4187', '--strictPort'], { cwd: root, stdio: 'ignore' });
let browser;

try {
  let ready = false;
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (server.exitCode !== null) throw new Error(`Vite exited with code ${server.exitCode}.`);
    try { ready = (await fetch(base)).ok; } catch { await delay(500); continue; }
    if (ready) break;
  }
  assert(ready, 'Vite did not start in time.');

  browser = await chromium.launch({ headless: true, ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.setDefaultTimeout(15000);
  const errors = [];
  let failSchemaRequest = false;
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (failSchemaRequest && path === '/api/v1/model/schema') return route.abort();
    const responses = {
      '/api/v1/health': { status: 200, body: { status: 'ok', service: 'netsight-api', model_loaded: false, model_version: null } },
      '/api/v1/analyses': { status: 200, body: { items: [], total: 0, limit: 10, offset: 0 } },
      '/api/v1/model/schema': { status: 200, body: { schema_name: 'unsw-nb15-flow-v1', feature_count: 1, features: ['dur'], numeric_features: ['dur'], categorical_features: [], excluded_columns: ['id', 'label', 'attack_cat'] } },
      '/api/v1/model/info': { status: 503, body: { error: { code: 503, message: 'No evaluated model is installed.' } } },
      '/api/v1/replays': { status: 200, body: { items: [] } },
    };
    const response = responses[path] ?? { status: 404, body: { error: { code: 404, message: 'Not found.' } } };
    await route.fulfill({ status: response.status, contentType: 'application/json', body: JSON.stringify(response.body) });
  });

  await page.goto(base, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.getByRole('heading', { name: 'Your network. In plain sight.' }).waitFor();
  await page.getByRole('link', { name: 'Enter Command Center' }).click();
  await page.getByRole('heading', { name: 'Command Center', exact: true }).waitFor();
  await page.locator('nav[aria-label="Workspace navigation"] a').last().waitFor();
  assert.equal(await page.locator('nav[aria-label="Workspace navigation"] a').count(), 5, 'Primary navigation should contain the five jury-demo modules.');
  for (const name of ['Network Pulse', 'Traffic Analyzer', 'Threat Investigation', 'Reports', 'Command Center']) {
    await page.locator('nav').getByRole('link', { name, exact: true }).click();
    await page.getByRole('heading', { name, exact: true, level: 1 }).waitFor();
  }
  await page.goto(`${base}/model-lab`);
  await page.getByRole('heading', { name: 'Model Lab', exact: true, level: 1 }).waitFor();
  failSchemaRequest = true;
  await page.goto(`${base}/traffic-analyzer`);
  await page.getByRole('alert').filter({ hasText: 'Cannot reach NetSight API. Check the backend connection and retry.' }).waitFor();
  failSchemaRequest = false;
  assert.deepEqual(errors, [], 'The app should render all six routes without browser errors.');
  console.log('PASS: all routes, mocked API states, and readable recovery when the model schema request fails.');
} finally {
  await browser?.close();
  server.kill();
}
