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
  let failHistoryRequest = false;
  let failWebRiskRequest = false;
  let failAuthRequest = false;
  let accessToken = '';
  page.on('pageerror', error => errors.push(error.message));
  const user = { id: '2a17d1c4-b2a8-4da5-976d-f5d46078b756', aud: 'authenticated', role: 'authenticated', email: 'analyst@netsight.test', app_metadata: { provider: 'email', providers: ['email'] }, user_metadata: {}, identities: [], created_at: new Date().toISOString() };
  const encode = value => Buffer.from(JSON.stringify(value)).toString('base64url');
  accessToken = `${encode({ alg: 'HS256', typ: 'JWT' })}.${encode({ sub: user.id, aud: 'authenticated', role: 'authenticated', email: user.email, exp: Math.floor(Date.now() / 1000) + 3600 })}.smoke`;
  const session = { access_token: accessToken, token_type: 'bearer', expires_in: 3600, refresh_token: 'smoke-refresh-token', user };
  await page.route(`${authUrl}/auth/v1/**`, async route => {
    const path = new URL(route.request().url()).pathname;
    if (failAuthRequest && path.endsWith('/otp')) return route.abort('failed');
    if (path.endsWith('/otp')) return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    if (path.endsWith('/verify')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(session) });
    if (path.endsWith('/recover')) return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    if (path.endsWith('/user')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(user) });
    if (path.endsWith('/logout')) return route.fulfill({ status: 204, body: '' });
    return route.fulfill({ status: 404, contentType: 'application/json', body: '{"msg":"Not found"}' });
  });
  await page.route('**/api/v1/**', async route => {
    assert.equal(route.request().headers().authorization, `Bearer ${accessToken}`, 'API requests must carry the Supabase session token.');
    const path = new URL(route.request().url()).pathname;
    if (failSchemaRequest && path === '/api/v1/model/schema') return route.abort();
    if (failHistoryRequest && path === '/api/v1/analyses') return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { code: 503, message: 'History unavailable.' } }) });
    if (failWebRiskRequest && path === '/api/v1/url/reputation') return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { code: 503, message: 'Google Web Risk rejected this project or API key. Check that Web Risk is enabled, billing is active, and the key is restricted to Web Risk API.' } }) });
    const responses = {
      '/api/v1/health': { status: 200, body: { status: 'ok', service: 'netsight-api', model_loaded: false, model_version: null } },
      '/api/v1/analyses': { status: 200, body: { items: [], total: 0, limit: 10, offset: 0 } },
      '/api/v1/model/schema': { status: 200, body: { schema_name: 'unsw-nb15-flow-v1', feature_count: 1, features: ['dur'], numeric_features: ['dur'], categorical_features: [], excluded_columns: ['id', 'label', 'attack_cat'] } },
      '/api/v1/model/info': { status: 503, body: { error: { code: 503, message: 'No evaluated model is installed.' } } },
      '/api/v1/replays': { status: 200, body: { items: [] } },
      '/api/v1/url/reputation': { status: 200, body: { provider: 'Google Web Risk', matched: true, threat_types: ['SOCIAL_ENGINEERING'], expires_at: '2026-11-20T12:00:00Z' } },
      '/api/v1/traffic/pcap/analyze': { status: 200, body: { filename: 'demo.pcap', packets_seen: 5, supported_packets: 5, flow_count: 2, captured_bytes: 420, flows: [{ source: '192.0.2.10:51514', destination: '198.51.100.20:443', protocol: 'TCP', packets: 3, captured_bytes: 300, source_packets: 2, destination_packets: 1, source_bytes: 200, destination_bytes: 100, duration_seconds: 0.5, first_seen: '2026-11-20T12:00:00Z', last_seen: '2026-11-20T12:00:00Z' }], limitations: ['Packet-derived flows are not sent to the ML classifier.'] } },
    };
    const response = responses[path] ?? { status: 404, body: { error: { code: 404, message: 'Not found.' } } };
    await route.fulfill({ status: response.status, contentType: 'application/json', body: JSON.stringify(response.body) });
  });

  await page.goto(`${base}/reports`);
  await page.getByRole('heading', { name: 'Sign in to NetLens AI' }).waitFor();
  await page.goto(`${base}/auth/signup`);
  await page.getByLabel('Email address').fill(user.email);
  await page.getByRole('button', { name: 'Create account' }).click();
  await page.getByRole('status').filter({ hasText: 'one-time code' }).waitFor();
  failAuthRequest = true;
  await page.getByRole('button', { name: 'Resend code' }).click();
  await page.getByRole('alert').filter({ hasText: 'Could not reach Supabase Auth.' }).waitFor();
  failAuthRequest = false;
  await page.getByLabel('One-time code from your email').fill('123456');
  await page.getByRole('button', { name: 'Verify code and sign in' }).click();
  await page.getByRole('heading', { name: 'Command Center', exact: true }).waitFor();
  await page.reload();
  assert.equal(await page.getByText(user.email).count(), 1, 'A persisted email-code session should restore the signed-in user after reload.');
  await page.getByRole('button', { name: 'Sign out' }).click();
  await page.getByRole('heading', { name: 'Sign in to NetLens AI' }).waitFor();
  await page.goto(`${base}/auth/forgot-password`);
  await page.getByLabel('Email address').fill(user.email);
  await page.getByRole('button', { name: 'Send recovery email' }).click();
  await page.getByRole('status').filter({ hasText: 'If the account exists' }).waitFor();
  await page.goto(`${base}/auth/reset-password`);
  await page.getByRole('heading', { name: 'Open your recovery link' }).waitFor();
  await page.goto(base, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.getByRole('heading', { name: /Your network\.\s*In plain sight\./ }).waitFor();
  await page.getByRole('link', { name: 'Enter Command Center' }).click();
  await page.getByRole('heading', { name: 'Sign in to NetLens AI' }).waitFor();
  await page.getByLabel('Email address').fill(user.email);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByRole('status').filter({ hasText: 'one-time code' }).waitFor();
  await page.getByLabel('One-time code from your email').fill('123456');
  await page.getByRole('button', { name: 'Verify code and sign in' }).click();
  await page.getByRole('heading', { name: 'Command Center', exact: true }).waitFor();
  await page.reload();
  await page.getByRole('heading', { name: 'Command Center', exact: true }).waitFor();
  assert.equal(await page.getByText(user.email).count(), 1, 'A persisted Supabase session should restore the signed-in user after reload.');
  await page.locator('nav.desktop-navigation[aria-label="Workspace navigation"] a').last().waitFor();
  assert.equal(await page.locator('nav.desktop-navigation[aria-label="Workspace navigation"] a').count(), 6, 'Primary navigation should contain all six workspace modules.');
  for (const name of ['Network Pulse', 'Traffic Analyzer', 'URL Check Demo', 'Threat Investigation', 'Reports', 'Command Center']) {
    await page.locator('nav.desktop-navigation').getByRole('link', { name, exact: true }).click();
    await page.getByRole('heading', { name, exact: true, level: 1 }).waitFor();
    if (name === 'URL Check Demo') {
      await page.getByRole('button', { name: 'Lookalike brand' }).click();
      await page.getByRole('heading', { name: 'Warning signs found' }).waitFor();
      assert.ok((await page.locator('.url-check-result').innerText()).includes('outside its common paypal.com domain'));
      await page.getByLabel(/I understand the URL will be shared/).check();
      failWebRiskRequest = true;
      await page.getByRole('button', { name: 'Check Google Web Risk' }).click();
      await page.getByRole('alert').filter({ hasText: 'billing is active' }).waitFor();
      failWebRiskRequest = false;
      await page.getByRole('button', { name: 'Check Google Web Risk' }).click();
      await page.getByRole('status').filter({ hasText: 'Google Web Risk match: SOCIAL_ENGINEERING' }).waitFor();
      await page.getByRole('button', { name: 'No common signals' }).click();
      await page.getByRole('heading', { name: 'No common warning signs' }).waitFor();
      await page.getByRole('button', { name: 'IPv6 address host' }).click();
      assert.ok((await page.locator('.url-check-result').innerText()).includes('uses an IP address'));
      await page.getByRole('button', { name: 'Lookalike character swap' }).click();
      assert.ok((await page.locator('.url-check-result').innerText()).includes('1/l character swap'));
    }
    if (name === 'Traffic Analyzer') {
      await page.locator('#capture-file').setInputFiles({ name: 'demo.pcap', mimeType: 'application/vnd.tcpdump.pcap', buffer: Buffer.from('mock capture') });
      await page.getByRole('button', { name: 'Analyze packet flows' }).click();
      await page.getByRole('region', { name: 'Packet-derived flows' }).getByText('192.0.2.10:51514').waitFor();
    }
  }
  await page.goto(`${base}/model-lab`);
  await page.getByRole('heading', { name: 'Model Lab', exact: true, level: 1 }).waitFor();
  failHistoryRequest = true;
  await page.goto(`${base}/traffic-analyzer`);
  await page.locator('.saved-history summary').click();
  assert.match(await page.locator('.saved-history').innerText(), /saved analyses include results and validated flow features/i);
  await page.locator('.saved-history [role="alert"]').filter({ hasText: 'History unavailable.' }).waitFor();
  failHistoryRequest = false;
  await page.locator('.saved-history').getByRole('button', { name: 'Refresh history' }).click();
  await page.locator('.saved-history [role="alert"]').waitFor({ state: 'hidden' });
  failSchemaRequest = true;
  await page.goto(`${base}/traffic-analyzer`);
  await page.getByRole('alert').filter({ hasText: 'Cannot reach NetSight API. Check the backend connection and retry.' }).waitFor();
  failSchemaRequest = false;
  await page.goto(`${base}/command-center`);
  await page.getByRole('button', { name: 'Sign out' }).click();
  await page.getByRole('heading', { name: 'Sign in to NetLens AI' }).waitFor();
  await page.goto(`${base}/reports`);
  await page.getByRole('heading', { name: 'Sign in to NetLens AI' }).waitFor();
  await page.getByRole('button', { name: 'Use password instead' }).click();
  await page.getByLabel('Password').waitFor();
  await page.getByRole('button', { name: 'Use an email code instead' }).click();
  await page.getByLabel('Password').waitFor({ state: 'hidden' });
  failAuthRequest = true;
  await page.getByLabel('Email address').fill(user.email);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByRole('alert').filter({ hasText: 'Could not reach Supabase Auth.' }).waitFor();
  failAuthRequest = false;
  await page.goto(`${base}/reports`);
  await page.getByRole('heading', { name: 'Sign in to NetLens AI' }).waitFor();
  assert.deepEqual(errors, [], 'The app should render all seven workspace modules without browser errors.');
  console.log('PASS: mocked Supabase sign-in/sign-out and network failure, protected routing, seven workspace modules, URL heuristics, and API states.');
} finally {
  await browser?.close();
  if (process.platform === 'win32' && server.pid) spawnSync('taskkill', ['/pid', String(server.pid), '/t', '/f'], { stdio: 'ignore' });
  else server.kill();
}
