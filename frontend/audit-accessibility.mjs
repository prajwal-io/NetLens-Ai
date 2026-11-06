import { chromium } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs';
const base=process.env.AUDIT_URL||'http://127.0.0.1:5173';
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const results=[];
for(const width of [1440,390]){
 const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'}); const page=await context.newPage();
 for(const path of ['/','/command-center','/network-pulse','/traffic-analyzer','/threat-investigation','/model-lab','/reports']){
  await page.goto(base+path);await page.getByRole('heading',{level:1}).waitFor();await page.waitForTimeout(500);
  const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
  const item={path,width,violations:result.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))};
  results.push(item);
  console.log(path,width,JSON.stringify(item.violations));
  await page.screenshot({path:'../docs/review-'+(path==='/'?'landing':path.slice(1))+'-'+width+'.png',fullPage:true});
 }
 await context.close();
}
fs.writeFileSync('../docs/accessibility-audit.json',JSON.stringify(results,null,2));
await browser.close();
if(results.some(r=>r.violations.length))process.exitCode=1;
