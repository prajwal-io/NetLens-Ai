import {chromium} from '@playwright/test';
const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const p=await b.newPage();await p.goto('http://127.0.0.1:5173/logo.svg');await p.screenshot({path:'../docs/vector-logo-preview.png'});await b.close();
