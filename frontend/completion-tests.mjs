import { chromium } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const base=process.env.AUDIT_URL||'http://127.0.0.1:4175';
const browser=await chromium.launch({executablePath:process.env.BROWSER_EXECUTABLE||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const context=await browser.newContext({viewport:{width:1440,height:1000}});
const page=await context.newPage();
const errors=[];page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto(base+'/command-center');await page.getByText('Backend connected',{exact:true}).waitFor();
 await page.getByText('Loaded / netsight-rf-unsw-v1',{exact:true}).waitFor();
 // Repeating background: real CSS cycle, pause persistence, reduced motion.
 assert.equal(await page.locator('.edge-signal').first().evaluate(e=>getComputedStyle(e).animationIterationCount),'infinite');
 await page.getByRole('button',{name:'Pause background animation',exact:true}).click();
 assert.equal(await page.locator('.topology-background').getAttribute('data-running'),'false');
 await page.reload();await page.getByRole('button',{name:'Resume background animation',exact:true}).waitFor();
 await page.getByRole('button',{name:'Resume background animation',exact:true}).click();
 // Remember the dashboard range across navigation and refresh.
 await page.getByLabel('Chart time window').selectOption('Last hour');
 await page.goto(base+'/model-lab');await page.goto(base+'/command-center');
 assert.equal(await page.getByLabel('Chart time window').inputValue(),'Last hour');
 await page.reload();assert.equal(await page.getByLabel('Chart time window').inputValue(),'Last hour');
 // Network zoom/selection state, and reset to the full diagram.
 await page.goto(base+'/network-pulse');
 await page.getByLabel('Inspect device').selectOption('remote');
 await page.getByRole('button',{name:'Zoom in network diagram',exact:true}).click();
 await page.getByLabel('Network zoom').filter({hasText:'125%'}).waitFor();
 await page.reload();assert.equal(await page.getByLabel('Inspect device').inputValue(),'remote');
 await page.getByRole('button',{name:'Reset diagram',exact:true}).click();
 assert.equal(await page.getByLabel('Inspect device').inputValue(),'workstation');
 // Upload prechecks, removal, real validation, and cancellation.
 await page.goto(base+'/traffic-analyzer');
 await page.getByLabel('Traffic CSV file').setInputFiles({name:'wrong.txt',mimeType:'text/plain',buffer:Buffer.from('a')});
 await page.getByRole('alert').filter({hasText:'.csv extension'}).waitFor();
 assert(await page.getByRole('button',{name:'Validate CSV',exact:true}).isDisabled());
 await page.getByRole('button',{name:'Remove selected file'}).click();
 await page.getByLabel('Traffic CSV file').setInputFiles('../data/samples/valid-flows.csv');
 await page.getByRole('button',{name:'Validate CSV',exact:true}).click();
 await page.getByText('6 rows validated',{exact:true}).waitFor();
 await page.getByRole('heading',{name:'Validation checks',exact:true}).waitFor();
 await page.getByText('6 rows passed structure and feature-type checks.',{exact:true}).waitFor();
 // Run actual backend inference and inspect a CSV exported from those predictions.
 await page.getByRole('button',{name:'Analyze flows',exact:true}).click();
 await page.getByRole('heading',{name:'Model analysis',exact:true}).waitFor();
 await page.getByText('Actual model output / netsight-rf-unsw-v1',{exact:true}).waitFor();
 const [predictionDownload]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Export predictions CSV',exact:true}).click()]);
 const predictionCsv=fs.readFileSync(await predictionDownload.path(),'utf8');
 assert(predictionCsv.startsWith('row_id,label,malicious_score,decision_threshold,model_version,source_file'));
 assert.equal(predictionCsv.trim().split(/\r?\n/).length,7);
 await page.getByRole('button',{name:'Validate CSV',exact:true}).click();
 await page.getByText('6 rows validated',{exact:true}).waitFor();
 await page.route('**/traffic/validate',async route=>{await new Promise(r=>setTimeout(r,800));try{await route.continue()}catch{}});
 await page.getByRole('button',{name:'Validate CSV',exact:true}).click();
 await page.getByRole('button',{name:'Cancel validation',exact:true}).click();
 await page.getByText('Validation cancelled.',{exact:false}).waitFor();
 await page.unrouteAll({behavior:'wait'});
 // The dashboard switches to this actual validation receipt without implying inference.
 await page.goto(base+'/command-center');
 await page.getByRole('button',{name:/Latest validation/}).click();
 await page.getByText('Validation only.',{exact:false}).waitFor();
 await page.getByText('Normal classifications',{exact:true}).waitFor();
 assert.equal(await page.getByText('Unavailable',{exact:true}).count(),2);
 await page.getByText('No classification timeline yet',{exact:true}).waitFor();
 assert.equal(await page.getByRole('heading',{name:'Recent sample flows',exact:true}).count(),0);
 await page.getByRole('button',{name:/Sample overview/}).click();
 await page.getByText('Sample UI data.',{exact:false}).waitFor();
 // The local network walkthrough is explicitly illustrative and has working controls.
 await page.goto(base+'/network-pulse');
 await page.getByText('not a historical replay',{exact:false}).waitFor();
 await page.getByRole('button',{name:'Play walkthrough',exact:true}).click();
 await page.getByRole('button',{name:'Pause walkthrough',exact:true}).waitFor();
 await page.getByRole('button',{name:/02 Name lookup/}).click();
 await page.getByRole('heading',{name:'Name lookup',exact:true}).waitFor();
 assert.equal(await page.locator('#walkthrough-position').inputValue(),'12');
 await page.getByRole('button',{name:'Restart',exact:true}).click();
 assert.equal(await page.locator('#walkthrough-position').inputValue(),'0');
 // Download and inspect the receipt generated from actual server validation.
 await page.goto(base+'/reports');
 await page.getByRole('button',{name:'Download validation receipt',exact:true}).waitFor();
 const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Download validation receipt',exact:true}).click()]);
 const receipt=JSON.parse(fs.readFileSync(await download.path(),'utf8'));
 assert.equal(receipt.kind,'csv-validation');assert.equal(receipt.rows,6);assert(!('predictions' in receipt));assert(!('preview' in receipt));
 await page.goto(base+'/model-lab');
 await page.getByRole('heading',{name:'Official held-out test',exact:true}).waitFor();
 await page.getByText('89.9%',{exact:true}).waitFor();
 await page.getByText('Evaluation caveat:',{exact:false}).waitFor();
 // Browser back/forward, sharable investigation state, filtering, sorting and focused mobile details.
 await page.goto(base+'/threat-investigation');
 await page.getByLabel('Classification',{exact:true}).selectOption('Normal');
 await page.getByText('1 of 4 sample flows',{exact:true}).waitFor();
 await page.getByLabel('Sort by',{exact:true}).selectOption('port');
 await page.reload();assert.equal(await page.getByLabel('Classification',{exact:true}).inputValue(),'Normal');
 await page.getByRole('button',{name:'Reset filters',exact:true}).click();
 await page.setViewportSize({width:390,height:900});
 await page.getByRole('button',{name:/FL-0281.*inspect sample flow/}).click();
 await page.getByRole('heading',{name:'FL-0281',exact:true}).waitFor();
 assert(!(await page.locator('.flow-list-pane').isVisible()));
 await page.goBack();assert(await page.locator('.flow-list-pane').isVisible());
 await page.goForward();await page.getByRole('heading',{name:'FL-0281',exact:true}).waitFor();
 await page.getByRole('button',{name:'Back to filtered flows',exact:true}).click();
 await page.getByRole('searchbox',{name:'Find an address, port, or flow ID'}).fill('no-such-flow');
 await page.getByText('0 of 4 sample flows',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Reset filters',exact:true}).click();
 // Offline state and recovery are explicit.
 await context.setOffline(true);await page.getByText('You are offline.',{exact:false}).waitFor();
 await context.setOffline(false);await page.getByText('Backend connected',{exact:true}).waitFor();
 // Narrow, landscape, desktop, and 200%-equivalent CSS viewport reflow.
 for(const viewport of [{width:320,height:900},{width:844,height:390},{width:720,height:500},{width:1440,height:1000}]){
  await page.setViewportSize(viewport);
  for(const path of ['/','/command-center','/network-pulse','/traffic-analyzer','/threat-investigation','/model-lab','/reports','/unknown-route']){
   await page.goto(base+path);await page.getByRole('heading',{level:1}).waitFor();
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Page overflow at '+JSON.stringify(viewport)+path);
  }
 }
 await page.setViewportSize({width:390,height:900});await page.goto(base+'/command-center');
 await page.locator('.mobile-navigation summary').click();
 const menuAudit=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();assert.deepEqual(menuAudit.violations.map(v=>v.id),[]);
 await page.emulateMedia({reducedMotion:'reduce'});
 assert.equal(await page.locator('.edge-signal').first().evaluate(e=>getComputedStyle(e).animationName),'none');
 assert.deepEqual(errors,[]);
 console.log('PASS: background controls, saved dashboard/network preferences, zoom/reset, CSV checks and cancellation, dashboard source switching without fake predictions, guided replay controls, receipt export, filters/history/mobile detail, offline recovery, responsive route overflow, 404, accessibility, and reduced motion.');
}finally{await browser.close()}
