import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
const base=process.env.AUDIT_URL||'http://127.0.0.1:4175';
const browser=await chromium.launch({executablePath:process.env.BROWSER_EXECUTABLE||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
try{
 const storageContext=await browser.newContext();
 await storageContext.addInitScript(()=>{Storage.prototype.setItem=function(){throw new DOMException('Storage blocked','SecurityError')}});
 const page=await storageContext.newPage();
 await page.goto(base);await page.getByRole('heading',{level:1}).waitFor();
 await page.getByRole('button',{name:'Pause background animation',exact:true}).click();
 await page.getByRole('button',{name:'Resume background animation',exact:true}).waitFor();
 assert.equal(await page.locator('.topology-background').getAttribute('data-running'),'false');
 await page.getByRole('button',{name:'Resume background animation',exact:true}).click();
 await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))});
 await page.waitForFunction(()=>document.querySelector('.topology-background')?.getAttribute('data-running')==='false');
 assert.equal(await page.locator('.topology-background').getAttribute('data-running'),'false');
 await storageContext.close();

 const recoveryContext=await browser.newContext();
 await recoveryContext.addInitScript(()=>{window.__originalResizeObserver=window.ResizeObserver;window.ResizeObserver=class{constructor(){throw new Error('Intentional recovery test')}}});
 const recovery=await recoveryContext.newPage();await recovery.goto(base+'/command-center');
 await recovery.getByRole('heading',{name:'This view could not load.',exact:true}).waitFor();
 await recovery.screenshot({path:'../docs/recovery-state.png'});
 await recovery.evaluate(()=>{window.ResizeObserver=window.__originalResizeObserver});
 await recovery.getByRole('button',{name:'Try this view again',exact:true}).click();
 await recovery.getByRole('heading',{name:'Command Center',exact:true,level:1}).waitFor();
 await recovery.getByLabel('Chart time window').waitFor();
 await recoveryContext.close();

 const loadingContext=await browser.newContext();
 const loading=await loadingContext.newPage();let release;
 const gate=new Promise(resolve=>{release=resolve});
 await loading.route('**/assets/Pulse-*',async route=>{await gate;try{await route.continue()}catch{}});
 await loading.goto(base+'/network-pulse',{waitUntil:'domcontentloaded'});
 await loading.getByText('Loading workspace...',{exact:true}).waitFor();
 await loading.screenshot({path:'../docs/loading-state.png'});
 release();
 await loading.getByRole('heading',{name:'Network Pulse',exact:true,level:1}).waitFor();
 await loadingContext.close();
 console.log('PASS: storage-disabled preferences, hidden-document animation pause, caught render failure/retry, and real route-loading skeleton.');
}finally{await browser.close()}
