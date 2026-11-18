import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';
import { chromium } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('.', import.meta.url));
const vite = fileURLToPath(new URL('./node_modules/vite/bin/vite.js', import.meta.url));
const base = 'http://127.0.0.1:4187';
const authUrl = 'https://netsight-smoke.supabase.co';
const smokeEnv = { ...process.env, VITE_SUPABASE_URL: authUrl, VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_smoke' };
const build = spawnSync(process.execPath, [vite, 'build', '--configLoader', 'runner'], { cwd: root, env: smokeEnv, encoding: 'utf8' });
if (build.status !== 0) throw new Error(`Vite production build failed:\n${build.stderr || build.stdout}`);
const server = spawn(process.execPath, [vite, 'preview', '--configLoader', 'runner', '--host', '127.0.0.1', '--port', '4187', '--strictPort'], {
  cwd: root, stdio: 'ignore', env: smokeEnv,
});
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
  let accessToken = '';
  page.on('pageerror', error => errors.push(error.message));
  const user = { id: '2a17d1c4-b2a8-4da5-976d-f5d46078b756', aud: 'authenticated', role: 'authenticated', email: 'analyst@netsight.test', app_metadata: { provider: 'email', providers: ['email'] }, user_metadata: {}, identities: [], created_at: new Date().toISOString() };
  const encode = value => Buffer.from(JSON.stringify(value)).toString('base64url');
  accessToken = `${encode({ alg: 'HS256', typ: 'JWT' })}.${encode({ sub: user.id, aud: 'authenticated', role: 'authenticated', email: user.email, exp: Math.floor(Date.now() / 1000) + 3600 })}.smoke`;
  const session = { access_token: accessToken, token_type: 'bearer', expires_in: 3600, refresh_token: 'smoke-refresh-token', user };
  await page.route(`${authUrl}/auth/v1/**`, async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/token')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(session) });
    if (path.endsWith('/signup')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user, session: null }) });
    if (path.endsWith('/recover')) return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    if (path.endsWith('/user')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(user) });
    if (path.endsWith('/logout')) return route.fulfill({ status: 204, body: '' });
    return route.fulfill({ status: 404, contentType: 'application/json', body: '{"msg":"Not found"}' });
  });
  await page.route('**/api/v1/**', async route => {
    assert.equal(route.request().headers().authorization, `Bearer ${accessToken}`, 'API requests must carry the Supabase session token.');
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

  await page.goto(`${base}/reports`);
  await page.getByRole('heading', { name: 'Sign in to NetLens AI' }).waitFor();
  await page.goto(`${base}/auth/signup`);
  await page.getByLabel('Email address').fill(user.email);
  await page.getByLabel('Password').fill('smoke-test-password');
  await page.getByRole('button', { name: 'Create account' }).click();
  await page.getByRole('status').filter({ hasText: 'Check your email for the confirmation link' }).waitFor();
  await page.goto(`${base}/auth/forgot-password`);
  await page.getByLabel('Email address').fill(user.email);
  await page.getByRole('button', { name: 'Send reset link' }).click();
  await page.getByRole('status').filter({ hasText: 'If the account exists' }).waitFor();
  await page.goto(`${base}/auth/reset-password`);
  await page.getByRole('heading', { name: 'Open your recovery link' }).waitFor();
  await page.goto(base, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.getByRole('heading', { name: 'Your network. In plain sight.' }).waitFor();
  await page.getByRole('link', { name: 'Enter Command Center' }).click();
  await page.getByRole('heading', { name: 'Sign in to NetLens AI' }).waitFor();
  await page.getByLabel('Email address').fill(user.email);
  await page.getByLabel('Password').fill('smoke-test-password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByRole('heading', { name: 'Command Center', exact: true }).waitFor();
  await page.locator('nav.desktop-navigation[aria-label="Workspace navigation"] a').last().waitFor();
  assert.equal(await page.locator('nav.desktop-navigation[aria-label="Workspace navigation"] a').count(), 5, 'Primary navigation should contain the five jury-demo modules.');
  for (const name of ['Network Pulse', 'Traffic Analyzer', 'Threat Investigation', 'Reports', 'Command Center']) {
    await page.locator('nav.desktop-navigation').getByRole('link', { name, exact: true }).click();
    await page.getByRole('heading', { name, exact: true, level: 1 }).waitFor();
  }
  await page.goto(`${base}/model-lab`);
  await page.getByRole('heading', { name: 'Model Lab', exact: true, level: 1 }).waitFor();
  failSchemaRequest = true;
  await page.goto(`${base}/traffic-analyzer`);
  await page.getByRole('alert').filter({ hasText: 'Cannot reach NetSight API. Check the backend connection and retry.' }).waitFor();
  failSchemaRequest = false;
  await page.goto(`${base}/command-center`);
  await page.getByRole('button', { name: 'Sign out' }).click();
  await page.getByRole('heading', { name: 'Sign in to NetLens AI' }).waitFor();
  await page.goto(`${base}/reports`);
  await page.getByRole('heading', { name: 'Sign in to NetLens AI' }).waitFor();
  assert.deepEqual(errors, [], 'The app should render all six routes without browser errors.');
  console.log('PASS: mocked Supabase sign-in/sign-out, protected routing, six routes, API states, and schema-error recovery.');
} finally {
  await browser?.close();
  server.kill();
}
