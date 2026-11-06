import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
await page.goto('http://127.0.0.1:5173');
const alpha=await page.evaluate(async()=>{
 const img=new Image();img.src='/logo-transparent.png';await img.decode();
 const canvas=document.createElement('canvas');canvas.width=img.width;canvas.height=img.height;
 const ctx=canvas.getContext('2d');ctx.drawImage(img,0,0);return ctx.getImageData(0,0,1,1).data[3];
});
assert.equal(alpha,0,'Logo background must be fully transparent');
console.log('PASS: actual alpha transparency');
for(const [width,name] of [[1440,'desktop'],[390,'mobile']]){
 await page.setViewportSize({width,height:1000});
 await page.screenshot({path:'../docs/logo-background-'+name+'.png'});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
}
await browser.close();
