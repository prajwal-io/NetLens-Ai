import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
const base=process.env.AUDIT_URL||'http://127.0.0.1:5173';
const browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(base+'/command-center');
await page.getByText('Backend connected',{exact:true}).waitFor();
await page.screenshot({path:'../docs/dashboard-desktop.png',fullPage:true});
for(const name of ['Network Pulse','Traffic Analyzer','Threat Investigation','Model Lab','Reports','Command Center']){
 await page.locator('nav').getByRole('link',{name,exact:true}).click();
 await page.getByRole('heading',{name,exact:true,level:1}).waitFor();
}
await page.goto(base+'/traffic-analyzer');
await page.getByLabel('Traffic CSV file').setInputFiles('../data/samples/valid-flows.csv');
await page.getByRole('button',{name:'Validate CSV',exact:true}).click();
await page.getByText('3 flows validated').waitFor();
await page.getByLabel('Traffic CSV file').setInputFiles({name:'invalid.csv',mimeType:'text/csv',buffer:Buffer.from('bad\n1')});
await page.getByRole('button',{name:'Validate CSV',exact:true}).click();
await page.getByRole('alert').filter({hasText:'Missing required columns'}).waitFor();
await page.route('**/api/v1/health',r=>r.abort());
await page.getByRole('button',{name:'Refresh backend status'}).click();
await page.getByText('Backend offline',{exact:true}).waitFor();
await page.getByRole('button',{name:'Retry connection'}).waitFor();
await page.unroute('**/api/v1/health');
await page.getByRole('button',{name:'Retry connection'}).click();
await page.getByText('Backend connected',{exact:true}).waitFor();
for(const width of [768,390]){
 await page.setViewportSize({width,height:1000});
 await page.goto(base+'/command-center');
 await page.locator('.mobile-navigation summary').click();
 await page.locator('nav').getByRole('link',{name:'Model Lab',exact:true}).click();
 await page.getByRole('heading',{name:'Model Lab',exact:true}).waitFor();
 for(const route of ['/command-center','/network-pulse','/traffic-analyzer','/threat-investigation','/model-lab','/reports']){
  await page.goto(base+route);
  await page.getByRole('heading',{level:1}).waitFor();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Page overflow at '+width+route);
 }
 await page.goto(base+'/command-center');
 await page.screenshot({path:'../docs/dashboard-'+width+'.png',fullPage:true});
}

await page.setViewportSize({width:1440,height:1000});
await page.goto(base);
await page.getByRole('heading',{name:'Your network. In plain sight.'}).waitFor();
await page.getByRole('button',{name:'Inspect Remote host',exact:true}).click();
await page.getByText('A highlighted connection illustrates', {exact:false}).waitFor();
await page.getByRole('button',{name:'Pause flow'}).click();
assert.equal(await page.locator('animateMotion').count(),0);
await page.getByRole('tab',{name:'Find the patterns'}).click();
await page.getByRole('tabpanel').getByText('Planned / Phase 2').waitFor();
await page.getByRole('tab',{name:'Find the patterns'}).press('ArrowLeft');
await page.getByRole('tabpanel').getByText('Available now').waitFor();
await page.getByRole('link',{name:'Enter Command Center'}).click();
await page.getByRole('heading',{name:'Command Center',exact:true,level:1}).waitFor();
for(const width of [1440,768,390]){
 await page.setViewportSize({width,height:1000});
 await page.goto(base);
 for(const id of ['the-problem','the-approach','how-it-works','capabilities']){
  await page.locator('#'+id).scrollIntoViewIfNeeded();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Landing overflow at '+width+id);
 }
 await page.screenshot({path:'../docs/landing-'+width+'.png',fullPage:true});
}
await page.emulateMedia({reducedMotion:'reduce'});
await page.goto(base);
assert.equal(await page.locator('animateMotion').count(),0);
await page.getByRole('link',{name:'Enter Command Center'}).click();
await page.getByRole('heading',{name:'Command Center',exact:true,level:1}).waitFor();

// Discoverable mobile navigation, Escape dismissal, and complete destination access.
await page.setViewportSize({width:390,height:1000});
await page.goto(base+'/command-center');
const menu=page.locator('.mobile-navigation');
await menu.locator('summary').click();
assert.equal(await menu.getByRole('link').count(),6);
await page.screenshot({path:'../docs/mobile-navigation.png'});
await menu.locator('summary').press('Escape');
assert.equal(await menu.getAttribute('open'),null);
await menu.locator('summary').click();
await menu.getByRole('link',{name:'Reports',exact:true}).click();
assert.equal(await menu.getAttribute('open'),null);
await page.getByRole('heading',{name:'Reports',exact:true,level:1}).waitFor();
await page.goto(base+'/threat-investigation');
await page.getByRole('button',{name:/FL-0281.*inspect sample flow/}).click();
await page.getByRole('heading',{name:'FL-0281',exact:true}).waitFor();
await page.goto(base+'/command-center');
await page.getByLabel('Chart time window').selectOption('Last hour');
await page.getByText('Sample snapshot | 11:00-11:45').waitFor();
await page.getByText('Read chart data',{exact:true}).click();
await page.getByRole('cell',{name:'370',exact:true}).waitFor();
await page.goto(base);
await page.keyboard.press('Tab');
await page.getByRole('link',{name:'Skip to content'}).press('Enter');
assert.equal(await page.evaluate(()=>document.activeElement?.id),'main-content');
assert.deepEqual(errors,[]);
await browser.close();
console.log('PASS: landing story, interactive SVG, keyboard process tabs, pause control, reduced motion, six routes, upload success and error, backend outage and retry, mobile navigation, responsive overflow, no browser errors.');
